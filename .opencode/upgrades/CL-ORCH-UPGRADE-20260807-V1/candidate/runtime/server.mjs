#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import {
  appendFileSync,
  chmodSync,
  closeSync,
  copyFileSync,
  cpSync,
  existsSync,
  fstatSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { readFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { pathToFileURL } from "node:url";

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { buildChildEnvironment, redactDiagnostic } from "./lib/security.mjs";
import { containsUnsafePublicText } from "./lib/public-text-security.mjs";
import {
  assertOriginOwns,
  deriveAttemptId,
  deriveOriginContext,
  deriveWorkspaceInstanceId,
  ensureProjectSecret,
  resolveProjectScope,
  projectStorePaths,
  resolveProjectId,
} from "./lib/identity.mjs";
import {
  assertManifestFresh,
  buildTextEvidenceManifest,
  canonicalHash,
  createReadReceipt,
  normalizeEvidenceContract,
  validateEvidenceResult,
} from "./lib/evidence-protocol.mjs";
import {
  contractErrorSemantics,
  DEFAULT_ROUTE_LIMITS,
  dependencySatisfied,
  isAcceptedResult,
  isDeterministicRequestRejection,
  isFallbackEligible,
  legacyStatus,
  normalizeResult,
  normalizeRouteConstraints,
} from "./lib/result-protocol.mjs";
import {
  createDurableTransmissionBudgetController,
} from "./lib/transmission-budget-controller.mjs";
import {
  estimateDeepSeekV4FlashPrompt,
} from "./lib/deepseek-v4-tokenizer.mjs";
import {
  CANDIDATE_DURABLE_ACCOUNTING_MODE,
  CANDIDATE_RUNTIME_MODE,
  createCandidateProjectRuntime,
} from "./lib/candidate-runtime.mjs";
import { resolveCapacityPolicy } from "./lib/capacity-policy.mjs";
import {
  CANDIDATE_DAEMON_PROFILE,
  CANDIDATE_DAEMON_RELEASE,
  CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
  CANDIDATE_DAEMON_RUNTIME_ACCEPTED,
  CANDIDATE_PROCESS_BOOT_ID,
} from "./lib/daemon-protocol-v2.mjs";
import {
  migrateSchedulerStoreToCandidateV3,
  migrateSchedulerStoreToCandidateV4,
  migrateSchedulerStoreToCandidateV5,
  openCandidateSchedulerStoreV5,
  openSchedulerStore,
} from "./lib/scheduler-store.mjs";
import {
  connectCandidateDaemonClientV2,
  createCandidateInactiveHeadRpcHandlers,
  createCandidateOrchestratorDaemonV2,
} from "./orchestrator-daemon.mjs";
import {
  runLocalExactWriteContract,
  runLocalReadContract,
} from "./local-executor.mjs";

const VERSION = "0.9.9";
const LOCAL_ROUTE_LABEL = "local-deterministic";
const LOCAL_EXACT_WRITE_MODEL = "local-exact-bytes-v1";
export const PROTOCOLS = Object.freeze({ contract: 4, evidence: 2, result: 3, store: 2 });
export const PROCESS_NAME = "DeepLuna";
const PRIMARY_PROFILES = Object.freeze({
  "deepseek-direct": Object.freeze({
    id: "deepseek-direct",
    displayName: "DeepLuna",
    provider: "deepseek",
    route: "deepseek-direct",
    apiUrl: "https://api.deepseek.com/chat/completions",
    credentialEnv: "DEEPSEEK_API_KEY",
    requestDialect: "deepseek",
    serviceTier: "standard",
    models: Object.freeze({
      FLASH: "deepseek-v4-flash",
      PRO: "deepseek-v4-flash",
      REASONING: "deepseek-v4-flash",
    }),
    reasoning: Object.freeze({ FLASH: "none", PRO: "high", REASONING: "max" }),
  }),
  "deepinfra-fast": Object.freeze({
    id: "deepinfra-fast",
    displayName: "DeepLuna Fast",
    provider: "deepinfra",
    route: "deepinfra-priority",
    apiUrl: "https://api.deepinfra.com/v1/openai/chat/completions",
    credentialEnv: "DEEPINFRA_API_TOKEN",
    requestDialect: "deepinfra-openai",
    serviceTier: "priority",
    models: Object.freeze({
      FLASH: "deepseek-ai/DeepSeek-V4-Flash-0731",
      PRO: "deepseek-ai/DeepSeek-V4-Flash-0731",
      REASONING: "deepseek-ai/DeepSeek-V4-Flash-0731",
    }),
    reasoning: Object.freeze({ FLASH: "none", PRO: "high", REASONING: "max" }),
  }),
  "deepinfra-normal": Object.freeze({
    id: "deepinfra-normal",
    displayName: "DeepLuna Normal",
    provider: "deepinfra",
    route: "deepinfra-standard",
    apiUrl: "https://api.deepinfra.com/v1/openai/chat/completions",
    credentialEnv: "DEEPINFRA_API_TOKEN",
    requestDialect: "deepinfra-openai",
    serviceTier: "standard",
    models: Object.freeze({
      FLASH: "deepseek-ai/DeepSeek-V4-Flash-0731",
      PRO: "deepseek-ai/DeepSeek-V4-Flash-0731",
      REASONING: "deepseek-ai/DeepSeek-V4-Flash-0731",
    }),
    reasoning: Object.freeze({ FLASH: "none", PRO: "high", REASONING: "max" }),
  }),
  "deepinfra-flex": Object.freeze({
    id: "deepinfra-flex",
    displayName: "DeepLuna Flex",
    provider: "deepinfra",
    route: "deepinfra-flex",
    apiUrl: "https://api.deepinfra.com/v1/openai/chat/completions",
    credentialEnv: "DEEPINFRA_API_TOKEN",
    requestDialect: "deepinfra-openai",
    serviceTier: "flex",
    models: Object.freeze({
      FLASH: "deepseek-ai/DeepSeek-V4-Flash-0731",
      PRO: "deepseek-ai/DeepSeek-V4-Flash-0731",
      REASONING: "deepseek-ai/DeepSeek-V4-Flash-0731",
    }),
    reasoning: Object.freeze({ FLASH: "none", PRO: "high", REASONING: "max" }),
  }),
  "cheapluna-chat": Object.freeze({
    id: "cheapluna-chat",
    displayName: "CheapLuna Chat",
    provider: "deepseek",
    route: "deepseek-chat",
    apiUrl: "https://api.deepseek.com/chat/completions",
    credentialEnv: "DEEPSEEK_API_KEY",
    requestDialect: "deepseek",
    serviceTier: "standard",
    models: Object.freeze({
      FLASH: "deepseek-v4-flash",
      PRO: "deepseek-v4-flash",
      REASONING: "deepseek-v4-flash",
    }),
    reasoning: Object.freeze({ FLASH: "none", PRO: "high", REASONING: "max" }),
  }),
});

export function resolvePrimaryProfile(
  requested = process.env.DEEPLUNA_PRIMARY_PROFILE ?? "deepseek-direct",
) {
  const id = String(requested ?? "").trim().toLowerCase();
  const profile = PRIMARY_PROFILES[id];
  if (!profile) throw new Error(`unknown primary profile: ${requested}`);
  return profile;
}

export function startupBanner(profile = resolvePrimaryProfile()) {
  return `${profile.displayName} ${VERSION} listening on stdio`;
}

export function readWindowsUserEnvironmentVariable(name, runner = spawnSync) {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(String(name ?? ""))) return "";
  const command = `[Environment]::GetEnvironmentVariable('${name}', 'User')`;
  try {
    const result = runner(
      "powershell.exe",
      ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
      { encoding: "utf8", windowsHide: true, maxBuffer: 64 * 1024 },
    );
    if (result?.error || Number(result?.status ?? 0) !== 0) return "";
    return String(result?.stdout ?? "").trim();
  } catch {
    return "";
  }
}

export function resolvePrimaryApiKey(profile = resolvePrimaryProfile(), {
  inherited = process.env[profile.credentialEnv],
  platform = process.platform,
  readUserEnv = readWindowsUserEnvironmentVariable,
} = {}) {
  if (platform === "win32") {
    const userScoped = String(readUserEnv(profile.credentialEnv) ?? "").trim();
    if (userScoped) return userScoped;
  }
  return String(inherited ?? "").trim();
}

export function resolveDeepSeekApiKey(options = {}) {
  return resolvePrimaryApiKey(resolvePrimaryProfile("deepseek-direct"), options);
}
export function resolveCodexOrchestrationEnabled(
  value = process.env.DEEPLUNA_CODEX_ORCHESTRATION,
) {
  const normalized = String(value ?? "enabled").trim().toLowerCase();
  if (["", "enabled", "true", "1", "on", "yes"].includes(normalized)) return true;
  if (["disabled", "false", "0", "off", "no"].includes(normalized)) return false;
  throw new Error(
    "DEEPLUNA_CODEX_ORCHESTRATION must be enabled/disabled, true/false, 1/0, on/off, or yes/no",
  );
}
export const LUNA_FALLBACK = Object.freeze({
  provider: "codex-chatgpt",
  model: "gpt-5.6-luna",
  reasoning: "xhigh",
  policy: "canonical-fallback-v4",
});
export const GLM_FALLBACK = Object.freeze({
  provider: "deepinfra",
  model: "deepseek-ai/DeepSeek-V4-Flash-0731",
  reasoning: "high",
  policy: "bounded-synthesis-v3",
  maxOutputTokens: 4_096,
  pricing: Object.freeze({
    verified_on: "2026-07-24",
    uncached_input_per_million_usd: 0.93,
    output_per_million_usd: 3,
  }),
});
export const FALLBACK_PROFILES = Object.freeze({
  LUNA: LUNA_FALLBACK,
  GLM: GLM_FALLBACK,
});
const FALLBACK_PROVIDER_SLOTS = Object.freeze({
  LUNA: { provider: "luna", readerIndex: 1, label: "Luna" },
  GLM: { provider: "glm", readerIndex: 2, label: "GLM" },
});
const FALLBACK_ROUTE_STATE_KEYS = Object.freeze({
  LUNA: "luna",
  GLM: "glm",
});
export const SOL_HEAD = Object.freeze({
  provider: "codex-chatgpt",
  model: "gpt-5.6-sol",
  efforts: Object.freeze(["medium", "high", "xhigh", "max"]),
  policy: "adaptive-sol-routing-v1",
});
const SOL_AUTHORITY_DOMAINS = Object.freeze([
  "architecture",
  "science",
  "hypothesis",
  "statistical_design",
  "publication_claim",
  "evidence_promotion",
  "security",
  "provenance",
  "canonical_runtime",
]);
const SOL_ROUTE_AXES = Object.freeze([
  "complexity",
  "scientific_claim_risk",
  "ambiguity",
  "blast_radius",
  "oracle_weakness",
]);
const DEFAULT_HEAD_ROUTING_POLICY = Object.freeze({
  mediumMaximum: 3,
  highMaximum: 7,
  minimumDelegatedWorkUnits: 4,
});

function normalizeFallbackRoute(route) {
  const normalized = String(route ?? "LUNA").toUpperCase();
  if (!FALLBACK_PROFILES[normalized]) {
    throw new Error(`unsupported fallback route: ${route}`);
  }
  return normalized;
}

export function resolveFallbackProfile(route = "LUNA") {
  return FALLBACK_PROFILES[normalizeFallbackRoute(route)];
}

function fallbackStateKey(route) {
  return normalizeFallbackRoute(route).toLowerCase();
}

function fallbackRouteProviderSlot(route) {
  const normalized = normalizeFallbackRoute(route);
  return FALLBACK_PROVIDER_SLOTS[normalized];
}

function fallbackProfileForProvider(provider) {
  if (provider === "luna") return FALLBACK_PROFILES.LUNA;
  if (provider === "glm") return FALLBACK_PROFILES.GLM;
  return null;
}

function normalizeFallbackProvider(provider) {
  const normalized = String(provider ?? "").toLowerCase();
  if (!["luna", "glm"].includes(normalized)) {
    throw new Error(`unsupported fallback provider: ${provider}`);
  }
  return normalized;
}

function fallbackRouteFromProvider(provider) {
  const normalized = String(provider ?? "").toUpperCase();
  if (normalized === "LUNA" || normalized === "GLM") return normalized.toLowerCase();
  return normalizeFallbackProvider(normalized);
}

function fallbackProviderLabel(routeOrProvider) {
  const normalized = String(routeOrProvider ?? "").toUpperCase();
  if (normalized === "LUNA" || normalized === "GLM") {
    return normalized;
  }
  const provider = normalizeFallbackProvider(normalized);
  return {
    luna: "Luna",
    glm: "GLM",
  }[provider];
}

function routeFromFallbackProvider(provider) {
  return normalizeFallbackProvider(provider) === "luna" ? "LUNA" : "GLM";
}

function boundedRouteInteger(raw, field, minimum, maximum) {
  const value = Number(raw?.[field]);
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${field} must be an integer between ${minimum} and ${maximum}`);
  }
  return value;
}

function normalizeAuthorityDomains(value) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error("authority_domains must be an array of authority domain strings");
  }
  const unique = [...new Set(value.map((item) => item.trim()).filter(Boolean))].sort();
  const unknown = unique.find((item) => !SOL_AUTHORITY_DOMAINS.includes(item));
  if (unknown) throw new Error(`unknown authority domain: ${unknown}`);
  return unique;
}

function hasCompleteMaxImpasse(raw, authorityDomains, valueAtRisk) {
  const impasse = raw?.xhigh_impasse;
  if (!impasse || typeof impasse !== "object" || Array.isArray(impasse)) return false;
  const alternatives = Array.isArray(impasse.alternatives)
    ? impasse.alternatives.filter((item) => typeof item === "string" && item.trim())
    : [];
  const evidenceLanes = Array.isArray(impasse.conflicting_evidence_lanes)
    ? impasse.conflicting_evidence_lanes.filter(
      (item) => typeof item === "string" && item.trim(),
    )
    : [];
  return (
    typeof impasse.attempt_fingerprint === "string" &&
    impasse.attempt_fingerprint.trim().length > 0 &&
    new Set(alternatives).size >= 2 &&
    new Set(evidenceLanes).size >= 2 &&
    impasse.material_consequence === true &&
    impasse.cheaper_resolution_exhausted === true &&
    impasse.prior_max_attempt === false &&
    authorityDomains.length > 0 &&
    valueAtRisk >= 2
  );
}

function boundedRouteText(value, field, maximum = 500) {
  if (value === undefined || value === null) return "";
  if (typeof value !== "string") throw new Error(`${field} must be a string`);
  const normalized = value.trim();
  if (normalized.length > maximum) throw new Error(`${field} exceeds ${maximum} characters`);
  return normalized;
}

function boundedRouteTextList(value, field) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`${field} must be an array of strings`);
  }
  if (value.length > 8) throw new Error(`${field} must contain at most 8 items`);
  return [...new Set(value.map((item) => boundedRouteText(item, field)).filter(Boolean))].sort();
}

function buildSolRouteContract(raw, route) {
  const impasse = raw.xhigh_impasse;
  let normalizedImpasse = null;
  if (impasse !== undefined && impasse !== null) {
    if (typeof impasse !== "object" || Array.isArray(impasse)) {
      throw new Error("xhigh_impasse must be an object");
    }
    normalizedImpasse = {
      attempt_fingerprint: boundedRouteText(
        impasse.attempt_fingerprint,
        "xhigh_impasse.attempt_fingerprint",
        256,
      ),
      alternatives: boundedRouteTextList(
        impasse.alternatives,
        "xhigh_impasse.alternatives",
      ),
      conflicting_evidence_lanes: boundedRouteTextList(
        impasse.conflicting_evidence_lanes,
        "xhigh_impasse.conflicting_evidence_lanes",
      ),
      material_consequence: impasse.material_consequence === true,
      cheaper_resolution_exhausted: impasse.cheaper_resolution_exhausted === true,
      prior_max_attempt: impasse.prior_max_attempt === true,
    };
  }
  return {
    authority_domains: [...route.authority_domains],
    complexity: boundedRouteInteger(raw, "complexity", 0, 3),
    scientific_claim_risk: boundedRouteInteger(raw, "scientific_claim_risk", 0, 3),
    ambiguity: boundedRouteInteger(raw, "ambiguity", 0, 3),
    blast_radius: boundedRouteInteger(raw, "blast_radius", 0, 3),
    oracle_weakness: boundedRouteInteger(raw, "oracle_weakness", 0, 3),
    value_at_risk: route.value_at_risk,
    mechanical: raw.mechanical === true,
    deterministic_oracle: raw.deterministic_oracle === true,
    estimated_work_units: boundedRouteInteger(raw, "estimated_work_units", 1, 1_000),
    current_effort: route.current_effort,
    xhigh_impasse: normalizedImpasse,
  };
}

export function classifySolRoute(raw, policy = DEFAULT_HEAD_ROUTING_POLICY) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("Sol route input must be an object");
  }
  const authorityDomains = normalizeAuthorityDomains(raw.authority_domains ?? []);
  const axes = Object.fromEntries(
    SOL_ROUTE_AXES.map((field) => [field, boundedRouteInteger(raw, field, 0, 3)]),
  );
  const valueAtRisk = boundedRouteInteger(raw, "value_at_risk", 0, 3);
  const currentEffort = String(raw.current_effort ?? "xhigh").trim().toLowerCase();
  if (!SOL_HEAD.efforts.includes(currentEffort)) {
    throw new Error(`current_effort must be one of ${SOL_HEAD.efforts.join(", ")}`);
  }
  const estimatedWorkUnits = boundedRouteInteger(raw, "estimated_work_units", 1, 1_000);
  if (raw.mechanical !== undefined && typeof raw.mechanical !== "boolean") {
    throw new Error("mechanical must be boolean");
  }
  if (raw.deterministic_oracle !== undefined && typeof raw.deterministic_oracle !== "boolean") {
    throw new Error("deterministic_oracle must be boolean");
  }
  const score = Object.values(axes).reduce((total, value) => total + value, 0);
  const reasons = [];
  const maxEligible = hasCompleteMaxImpasse(raw, authorityDomains, valueAtRisk);

  if (
    raw.mechanical === true &&
    raw.deterministic_oracle === true &&
    authorityDomains.length === 0 &&
    score <= policy.mediumMaximum &&
    !maxEligible
  ) {
    return Object.freeze({
      policy: SOL_HEAD.policy,
      action: "DELEGATE_DEEPLUNA",
      switch_scope: "ADVISORY_CURRENT_TURN",
      selected_effort: null,
      current_effort: currentEffort,
      score,
      value_at_risk: valueAtRisk,
      authority_domains: Object.freeze(authorityDomains),
      max_eligible: false,
      reasons: Object.freeze(["Deterministic mechanical work is eligible for DeepLuna."]),
    });
  }

  let selectedEffort = score <= policy.mediumMaximum
    ? "medium"
    : score <= policy.highMaximum
      ? "high"
      : "xhigh";
  reasons.push(`Reasoning score ${score} selected ${selectedEffort}.`);
  if (authorityDomains.length > 0) {
    selectedEffort = "xhigh";
    reasons.push(`Authority floor requires xhigh: ${authorityDomains.join(", ")}.`);
  }
  if (maxEligible) {
    selectedEffort = "max";
    reasons.push("Every one-shot Max escalation gate is satisfied.");
  }

  const effortOrder = new Map(SOL_HEAD.efforts.map((effort, index) => [effort, index]));
  const sameEffort = selectedEffort === currentEffort;
  const cheaperThanCurrent = effortOrder.get(selectedEffort) < effortOrder.get(currentEffort);
  const overheadDominates =
    cheaperThanCurrent && estimatedWorkUnits < policy.minimumDelegatedWorkUnits;
  const action = sameEffort || overheadDominates ? "HANDLE_CURRENT" : "START_SOL_HEAD";
  if (sameEffort) reasons.push("The active effort already matches the selected effort.");
  if (overheadDominates) {
    reasons.push("A separate lower-effort job would cost more than handling this small task now.");
  }
  return Object.freeze({
    policy: SOL_HEAD.policy,
    action,
    switch_scope: action === "START_SOL_HEAD"
      ? "NEW_JOB_ELIGIBLE"
      : "ADVISORY_CURRENT_TURN",
    selected_effort: selectedEffort,
    current_effort: currentEffort,
    score,
    value_at_risk: valueAtRisk,
    authority_domains: Object.freeze(authorityDomains),
    max_eligible: maxEligible,
    reasons: Object.freeze(reasons),
  });
}
const LEGACY_HANDOFF_KEYS = Object.freeze([
  "status",
  "summary",
  "files_inspected",
  "files_changed",
  "commands_run",
  "tests",
  "positive_findings",
  "negative_findings",
  "scientific_uncertainty",
  "architecture_uncertainty",
  "scope_deviation",
  "residual_risks",
  "recommended_next_action",
]);
const HANDOFF_KEYS = Object.freeze([
  ...LEGACY_HANDOFF_KEYS,
  "execution_status",
  "evidence_verdict",
]);
const HEAD_ACTIONS = Object.freeze([
  "RETURN_DECISION",
  "REQUEST_EVIDENCE",
  "DELEGATE_BOUNDED",
  "DOWNGRADE",
  "BLOCKED",
]);
const HEAD_HANDOFF_KEYS = Object.freeze([
  "action",
  "summary",
  "evidence_paths",
  "decision",
  "requested_evidence",
  "bounded_delegations",
  "recommended_effort",
  "scientific_uncertainty",
  "architecture_uncertainty",
  "residual_risks",
  "recommended_next_action",
]);
const CREDENTIAL_PATTERN = /(^|\/)(\.env(?:\..*)?|credentials?|secrets?)(\/|$)/i;
const ALWAYS_FORBIDDEN_COMMAND =
  /(?:git\s+(?:add|commit|push|pull|merge|rebase|reset|checkout|switch|clean)|\.env|credentials?|secrets?|\$env:|get-childitem\s+env:|invoke-webrequest|invoke-restmethod|\bcurl\b|\bwget\b)/i;
const READ_ONLY_WRITE_COMMAND =
  /(?:^|[\s;|])(?:set-content|add-content|out-file|remove-item|move-item|copy-item|new-item|rm|del|erase|mv|cp)(?:\s|$)|(?:^|[^<])>{1,2}(?!=)/i;
const IGNORED_DIRECTORIES = new Set([".git", ".venv", "node_modules", ".cache", ".archive"]);
const MAX_PROMPT_CHARS = 24_000;
export const MAX_TOOL_TURNS = 5;
export const MAXIMUM_PROVIDER_CALLS_EXHAUSTED = "MAXIMUM_PROVIDER_CALLS_EXHAUSTED";
export const WORKER_POLICY_VERSION = "worker-policy-v12";
export const COST_POLICY_VERSION = "cost-policy-v8";
export const PRICE_ESTIMATOR_VERSION =
  "deepinfra-v4-flash-priority-2026-07-25";
export const PRICE_ESTIMATOR_VERSION_STANDARD =
  "deepinfra-v4-flash-standard-2026-07-25";
export const PRICE_ESTIMATOR_VERSION_FLEX =
  "deepinfra-v4-flash-flex-2026-07-25";
export const PRICE_ESTIMATOR_VERSION_PRIORITY_REASONING =
  "deepinfra-v4-flash-priority-high-2026-07-25";
export const PRICE_ESTIMATOR_VERSION_STANDARD_REASONING =
  "deepinfra-v4-flash-standard-high-2026-07-25";
export const PRICE_ESTIMATOR_VERSION_FLEX_REASONING =
  "deepinfra-v4-flash-flex-high-2026-07-25";
export const V4_PRO_PRICE_ESTIMATOR_VERSION =
  "deepinfra-v4-pro-priority-2026-07-28";
export const NEMOTRON_PRICE_ESTIMATOR_VERSION =
  "deepinfra-nemotron-3-ultra-priority-2026-07-25";
export const GLM_PRICE_ESTIMATOR_VERSION =
  "deepinfra-glm-5.2-priority-2026-07-24";
export const DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION =
  "deepseek-v4-flash-chat-2026-08-05";
export const DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION_HIGH =
  "deepseek-v4-flash-chat-high-2026-08-07";
export const DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION_MAX =
  "deepseek-v4-flash-chat-max-2026-08-07";
export const PROMPT_SCHEMA_VERSION = "worker-prompt-v11";
export const RESULT_SCHEMA_VERSION = "worker-result-v8";
export const DEEPSEEK_V4_FLASH_NANO_USD = Object.freeze({
  cached_input: 3,
  uncached_input: 140,
  output: 280,
});
export const DEEPINFRA_V4_FLASH_NANO_USD = Object.freeze({
  cached_input: 27,
  uncached_input: 135,
  output: 270,
});
export const DEEPINFRA_V4_FLASH_STANDARD_NANO_USD = Object.freeze({
  cached_input: 18,
  uncached_input: 90,
  output: 180,
});
export const DEEPINFRA_V4_FLASH_FLEX_NANO_USD = Object.freeze({
  cached_input: 14,
  uncached_input: 72,
  output: 144,
});
export const DEEPINFRA_V4_PRO_PRIORITY_NANO_USD = Object.freeze({
  cached_input: 150,
  uncached_input: 1_950,
  output: 3_900,
});
export const DEEPINFRA_NEMOTRON_3_ULTRA_PRIORITY_NANO_USD = Object.freeze({
  cached_input: 150,
  uncached_input: 750,
  output: 3_300,
});
export const DEEPINFRA_GLM_5_2_PRIORITY_NANO_USD = Object.freeze({
  cached_input: 270,
  uncached_input: 1_395,
  output: 4_500,
});
export const DEEPLUNA_DURABLE_PRICING_CATALOG = Object.freeze({
  [PRICE_ESTIMATOR_VERSION]: Object.freeze({
    route: "FLASH",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Flash-0731",
    serviceTier: "priority",
    reasoningEffort: "none",
    rates: DEEPINFRA_V4_FLASH_NANO_USD,
  }),
  [PRICE_ESTIMATOR_VERSION_STANDARD]: Object.freeze({
    route: "FLASH",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Flash-0731",
    serviceTier: "standard",
    reasoningEffort: "none",
    rates: DEEPINFRA_V4_FLASH_STANDARD_NANO_USD,
  }),
  [PRICE_ESTIMATOR_VERSION_FLEX]: Object.freeze({
    route: "FLASH",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Flash-0731",
    serviceTier: "flex",
    reasoningEffort: "none",
    rates: DEEPINFRA_V4_FLASH_FLEX_NANO_USD,
  }),
  [PRICE_ESTIMATOR_VERSION_PRIORITY_REASONING]: Object.freeze({
    route: "FLASH",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Flash-0731",
    serviceTier: "priority",
    reasoningEffort: "high",
    rates: DEEPINFRA_V4_FLASH_NANO_USD,
  }),
  [PRICE_ESTIMATOR_VERSION_STANDARD_REASONING]: Object.freeze({
    route: "FLASH",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Flash-0731",
    serviceTier: "standard",
    reasoningEffort: "high",
    rates: DEEPINFRA_V4_FLASH_STANDARD_NANO_USD,
  }),
  [PRICE_ESTIMATOR_VERSION_FLEX_REASONING]: Object.freeze({
    route: "FLASH",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Flash-0731",
    serviceTier: "flex",
    reasoningEffort: "high",
    rates: DEEPINFRA_V4_FLASH_FLEX_NANO_USD,
  }),
  [V4_PRO_PRICE_ESTIMATOR_VERSION]: Object.freeze({
    route: "V4_PRO",
    provider: "deepinfra",
    model: "deepseek-ai/DeepSeek-V4-Pro",
    serviceTier: "priority",
    reasoningEffort: "none",
    rates: DEEPINFRA_V4_PRO_PRIORITY_NANO_USD,
  }),
  [NEMOTRON_PRICE_ESTIMATOR_VERSION]: Object.freeze({
    route: "NEMOTRON",
    provider: "deepinfra",
    model: "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B",
    serviceTier: "priority",
    reasoningEffort: "high",
    rates: DEEPINFRA_NEMOTRON_3_ULTRA_PRIORITY_NANO_USD,
  }),
  [GLM_PRICE_ESTIMATOR_VERSION]: Object.freeze({
    route: "GLM",
    provider: GLM_FALLBACK.provider,
    model: GLM_FALLBACK.model,
    serviceTier: "priority",
    reasoningEffort: GLM_FALLBACK.reasoning,
    rates: DEEPINFRA_GLM_5_2_PRIORITY_NANO_USD,
  }),
  [DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION]: Object.freeze({
    route: "FLASH",
    provider: "deepseek",
    model: "deepseek-v4-flash",
    serviceTier: "standard",
    reasoningEffort: "none",
    rates: DEEPSEEK_V4_FLASH_NANO_USD,
  }),
  [DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION_HIGH]: Object.freeze({
    route: "FLASH_HIGH",
    provider: "deepseek",
    model: "deepseek-v4-flash",
    serviceTier: "standard",
    reasoningEffort: "high",
    rates: DEEPSEEK_V4_FLASH_NANO_USD,
  }),
  [DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION_MAX]: Object.freeze({
    route: "FLASH_MAX",
    provider: "deepseek",
    model: "deepseek-v4-flash",
    serviceTier: "standard",
    reasoningEffort: "max",
    rates: DEEPSEEK_V4_FLASH_NANO_USD,
  }),
});
export const MAX_DURABLE_INPUT_TOKENS_PER_CALL = 8 * 1024 * 1024;
export const MAX_DURABLE_OUTPUT_TOKENS_PER_CALL = 8_192;

export function createDeepLunaDurableBudgetController({
  store,
  projectId,
  originId,
  projectCeilingNanoUsd,
  maximumInputTokensPerCall = MAX_DURABLE_INPUT_TOKENS_PER_CALL,
  maximumOutputTokensPerCall = MAX_DURABLE_OUTPUT_TOKENS_PER_CALL,
} = {}) {
  return createDurableTransmissionBudgetController({
    store,
    projectId,
    originId,
    projectCeilingNanoUsd,
    costPolicyVersion: COST_POLICY_VERSION,
    pricingCatalog: DEEPLUNA_DURABLE_PRICING_CATALOG,
    maximumInputTokensPerCall,
    maximumOutputTokensPerCall,
  });
}
export const CACHE_POLICY_IDENTITY = Object.freeze({
  worker: WORKER_POLICY_VERSION,
  cost: COST_POLICY_VERSION,
  estimator: PRICE_ESTIMATOR_VERSION,
  promptSchema: PROMPT_SCHEMA_VERSION,
  resultSchema: RESULT_SCHEMA_VERSION,
});
// Exact LOCAL-only work can use compact deterministic receipts. Provider-capable
// handoffs need enough room for the complete structured result contract.
const MIN_LOCAL_OUTPUT_TOKENS = 256;
const MIN_HANDOFF_OUTPUT_TOKENS = 3_000;
const OUTPUT_TOKEN_BOUNDS_DESCRIPTION =
  "Per-call output ceiling. Exact LOCAL_ONLY routes: 256-8192. " +
  "Provider-capable routes: 3000-8192.";
const MAX_LOCAL_ASSERTIONS = 32;
const MAX_LOCAL_ASSERTION_PATTERN_CHARS = 512;
export const LOCAL_COMMAND_POLICY_VERSION = 1;
export const LOCAL_EXACT_WRITE_POLICY_VERSION = 1;
const MAX_LOCAL_COMMANDS = 8;
const MAX_LOCAL_COMMAND_CHARS = 1_000;
const MAX_LOCAL_OUTPUT_BYTES = 64 * 1024;
const MAX_LOCAL_RECEIPT_STREAM_BYTES = 4 * 1024;
const LOCAL_RUNTIME_IDENTITY = Object.freeze({
  platform: process.platform,
  arch: process.arch,
  node: process.versions.node,
});
const MAX_TOOL_RESULT_CHARS = 64_000;
const GLM_PACKED_EVIDENCE_MODE = "GLM_PACKED_EVIDENCE_V1";
const FLASH_PACKED_EVIDENCE_MODE = "FLASH_PACKED_EVIDENCE_V1";
const FLASH_PACKED_WRITE_MODE = "FLASH_PACKED_WRITE_V1";
const FLASH_PACKED_PROMPT_SCHEMA_VERSION = "flash-packed-prompt-v8";
const FLASH_PACKED_HANDOFF_SCHEMA_MARKER = "FLASH_PACKED_HANDOFF_SCHEMA_V6";
const FLASH_PACKED_HANDOFF_EXAMPLE_MARKER = "FLASH_PACKED_HANDOFF_EXAMPLE_V6";
const FLASH_PACKED_HANDOFF_SCHEMA = Object.freeze({
  root: Object.freeze({
    positive_findings: "required array<finding>",
    negative_findings: "required array<finding>",
  }),
  finding: Object.freeze({
    text: "non-empty string",
    citation: Object.freeze({
      evidence_id: "exact receipted provider evidence_id",
      start: "integer inside that receipt range",
      end: "integer >= start and inside that receipt range",
      unit: "line",
    }),
  }),
});
const FLASH_PACKED_HANDOFF_EXAMPLE = Object.freeze({
  positive_findings: Object.freeze([Object.freeze({
    text: "finding text",
    citation: Object.freeze({
      evidence_id: `EV-${"0".repeat(32)}`,
      start: 1,
      end: 1,
      unit: "line",
    }),
  })]),
  negative_findings: Object.freeze([]),
});
const FLASH_PACKED_OBSERVABILITY_SCHEMA_VERSION = 1;
const MAX_GLM_PACKED_PROMPT_CHARS = 1_000_000;
const MAX_FLASH_PACKED_REQUEST_BODY_BYTES = 1_000_000;
const MAX_GLM_PACKED_SECTIONS = 128;
const CONSERVATIVE_PROMPT_CHARS_PER_TOKEN = 3;
// A byte-level tokenizer cannot emit more ordinary tokens than UTF-8 bytes. Keep
// additional proportional and fixed room for chat-template and tool-schema markers.
const CONSERVATIVE_INPUT_TOKEN_MARGIN_BASIS_POINTS = 1_000;
const CONSERVATIVE_INPUT_TOKEN_FIXED_MARGIN = 1_024;
const MAX_READ_FILE_BYTES = 2 * 1024 * 1024;
const MAX_READ_LINES = 400;
const MAX_WRITE_CHARS = 500_000;
export const FROZEN_ARTIFACT_POLICY_VERSION = 1;
const MAX_FROZEN_ARTIFACTS = 8;
const MAX_FROZEN_ARTIFACT_BYTES = 128 * 1024;
const MAX_FROZEN_ARTIFACT_TOTAL_BYTES = 256 * 1024;
const MAX_FROZEN_ARTIFACT_BASE64_CHARS =
  Math.ceil(MAX_FROZEN_ARTIFACT_BYTES / 3) * 4;
const MAX_WRITE_VERIFICATIONS = 1;
const MAX_WRITE_VERIFICATION_BYTES = 32 * 1024;
const MAX_LOCAL_EXACT_WRITE_BASE64_CHARS =
  Math.ceil(MAX_WRITE_VERIFICATION_BYTES / 3) * 4;
const MAX_LIST_FILES = 500;
const MAX_SEARCH_RESULTS = 100;
const MAX_COMMAND_OUTPUT_CHARS = 100_000;
const MAX_CACHE_FILES = 2_000;
const MAX_CACHE_BYTES = 100 * 1024 * 1024;

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map((item) => stableJson(item)).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function opaqueProjectIdentity(projectSecret, domain, value) {
  const secret = Buffer.from(String(projectSecret), "hex");
  if (secret.length < 16) throw new Error("project secret is invalid");
  return crypto
    .createHmac("sha256", secret)
    .update(`${domain}\0${String(value)}`, "utf8")
    .digest("hex");
}

function atomicJson(filePath, value) {
  mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${crypto.randomBytes(4).toString("hex")}.tmp`;
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  renameSync(temporary, filePath);
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

const NEGATIVE_ADMISSION_SCHEMA_VERSION = 1;
const NEGATIVE_ADMISSION_TTL_MS = 10 * 60 * 1_000;
const NEGATIVE_ADMISSION_WAIT_MS = 5_000;
const MAX_NEGATIVE_ADMISSION_BYTES = 4 * 1024;
const NEGATIVE_ADMISSION_BUSY_TIMEOUT_MS = 5_000;
const NEGATIVE_ADMISSION_SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS records (
  key TEXT PRIMARY KEY,
  record_json TEXT NOT NULL,
  expires_at_ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
  key TEXT PRIMARY KEY,
  owner_token TEXT NOT NULL,
  owner_pid INTEGER NOT NULL,
  identity_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL
);
`;

function negativeAdmissionIdentity(raw) {
  const identity = {
    schema_version: NEGATIVE_ADMISSION_SCHEMA_VERSION,
    project_id: String(raw.projectId ?? ""),
    request_identity_hash: String(raw.requestIdentityHash ?? ""),
    model: String(raw.model ?? ""),
    tier: String(raw.tier ?? ""),
    reasoning: String(raw.reasoning ?? ""),
    worker_policy_version: String(raw.workerPolicyVersion ?? ""),
  };
  if (!/^[A-Za-z0-9._:-]{1,256}$/.test(identity.project_id)) {
    throw new Error("negative admission project identity is invalid");
  }
  if (!/^[a-f0-9]{64}$/.test(identity.request_identity_hash)) {
    throw new Error("negative admission request identity is invalid");
  }
  for (const key of ["model", "tier", "reasoning", "worker_policy_version"]) {
    if (!identity[key] || identity[key].length > 256) {
      throw new Error(`negative admission ${key} is invalid`);
    }
  }
  return Object.freeze(identity);
}

function negativeAdmissionRecordValid(record, identity, key, nowMs) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return false;
  const integrity = record.integrity_hash;
  const core = { ...record };
  delete core.integrity_hash;
  return record.key === key &&
    stableJson(Object.fromEntries(
      Object.keys(identity).map((field) => [field, record[field]]),
    )) === stableJson(identity) &&
    [400, 422].includes(record.http_status) &&
    record.rejection_class === "DETERMINISTIC_REQUEST_REJECTED" &&
    record.cost_policy_version === COST_POLICY_VERSION &&
    Number.isSafeInteger(record.created_at_ms) &&
    Number.isSafeInteger(record.expires_at_ms) &&
    record.created_at_ms <= nowMs &&
    record.expires_at_ms > nowMs &&
    integrity === sha256(stableJson(core));
}

function asyncDelay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function negativeAdmissionWaitTimeout() {
  const error = new Error("negative admission waiter exceeded its bounded wait");
  Object.defineProperties(error, {
    code: { value: "NEGATIVE_ADMISSION_WAIT_TIMEOUT", enumerable: true },
    executionStatus: { value: "BLOCKED", enumerable: true },
    deepseekFailureClass: { value: "LOCAL_CONTRACT" },
  });
  return error;
}

function negativeAdmissionOwnerFenced() {
  const error = new Error("negative admission owner token was fenced by a replacement");
  Object.defineProperties(error, {
    code: { value: "NEGATIVE_ADMISSION_OWNER_FENCED", enumerable: true },
    executionStatus: { value: "BLOCKED", enumerable: true },
    deepseekFailureClass: { value: "LOCAL_CONTRACT" },
  });
  return error;
}

function negativeAdmissionOwnerAlive(processAliveFunction, pid) {
  try {
    // PID reuse is handled conservatively: any live PID remains an owner and is
    // never stolen by age. A waiter may time out, but it cannot duplicate a call.
    return processAliveFunction(pid) !== false;
  } catch {
    return true;
  }
}

export function createNegativeAdmissionCoordinator(
  projectRoot,
  {
    nowFunction = Date.now,
    ttlMs = NEGATIVE_ADMISSION_TTL_MS,
    waitMs = NEGATIVE_ADMISSION_WAIT_MS,
    waitNowFunction = Date.now,
    processAliveFunction = processAlive,
  } = {},
) {
  const root = path.join(path.resolve(projectRoot), "negative-admission-v1");
  const databasePath = path.join(root, "admission.sqlite");
  mkdirSync(root, { recursive: true });

  const withDatabase = (operation) => {
    const database = new DatabaseSync(databasePath);
    try {
      database.exec(`PRAGMA busy_timeout=${NEGATIVE_ADMISSION_BUSY_TIMEOUT_MS};`);
      database.exec("PRAGMA journal_mode=DELETE;");
      database.exec("PRAGMA synchronous=FULL;");
      database.exec(NEGATIVE_ADMISSION_SCHEMA_SQL);
      return operation(database);
    } finally {
      database.close();
    }
  };

  const immediate = (database, operation) => {
    database.exec("BEGIN IMMEDIATE;");
    try {
      const result = operation();
      database.exec("COMMIT;");
      return result;
    } catch (error) {
      try {
        database.exec("ROLLBACK;");
      } catch {
        // Preserve the original transactional error.
      }
      throw error;
    }
  };

  const admittedRecord = (database, identity, key, nowMs) => {
    const row = database.prepare(
      "SELECT record_json FROM records WHERE key = ?",
    ).get(key);
    if (!row || Buffer.byteLength(row.record_json, "utf8") > MAX_NEGATIVE_ADMISSION_BYTES) {
      return null;
    }
    try {
      const record = JSON.parse(row.record_json);
      return negativeAdmissionRecordValid(record, identity, key, nowMs)
        ? Object.freeze(record)
        : null;
    } catch {
      return null;
    }
  };

  // Initialize and close once. Every later operation owns and closes its handle,
  // which keeps Windows cleanup deterministic and avoids lingering WAL/SHM files.
  withDatabase(() => null);

  return Object.freeze({
    root,
    databasePath,
    async claim(rawIdentity) {
      const identity = negativeAdmissionIdentity(rawIdentity);
      const key = sha256(stableJson(identity));
      const deadline = waitNowFunction() + waitMs;
      while (true) {
        const token = crypto.randomBytes(16).toString("hex");
        const claimed = withDatabase((database) => immediate(database, () => {
          const nowMs = nowFunction();
          const admitted = admittedRecord(database, identity, key, nowMs);
          if (admitted) return { kind: "ADMITTED", key, record: admitted };
          const existingRecord = database.prepare(
            "SELECT 1 AS present FROM records WHERE key = ?",
          ).get(key);
          if (existingRecord) {
            database.prepare("DELETE FROM records WHERE key = ?").run(key);
          }
          const claim = database.prepare(
            "SELECT owner_token, owner_pid FROM claims WHERE key = ?",
          ).get(key);
          if (!claim) {
            database.prepare(
              "INSERT INTO claims (key, owner_token, owner_pid, identity_json, created_at_ms) " +
                "VALUES (?, ?, ?, ?, ?)",
            ).run(key, token, process.pid, stableJson(identity), nowMs);
            return { kind: "OWNER", key, token };
          }
          if (negativeAdmissionOwnerAlive(processAliveFunction, Number(claim.owner_pid))) {
            return { kind: "WAIT", key };
          }
          const replaced = database.prepare(
            "UPDATE claims SET owner_token = ?, owner_pid = ?, identity_json = ?, " +
              "created_at_ms = ? WHERE key = ? AND owner_token = ?",
          ).run(token, process.pid, stableJson(identity), nowMs, key, claim.owner_token);
          return replaced.changes === 1
            ? { kind: "OWNER", key, token }
            : { kind: "WAIT", key };
        }));
        if (claimed.kind === "ADMITTED") {
          return Object.freeze(claimed);
        }
        if (claimed.kind === "OWNER") {
          let released = false;
          const assertOwner = (database) => {
            const row = database.prepare(
              "SELECT owner_token FROM claims WHERE key = ?",
            ).get(key);
            if (!row || row.owner_token !== claimed.token) {
              throw negativeAdmissionOwnerFenced();
            }
          };
          const release = () => {
            if (released) return;
            withDatabase((database) => immediate(database, () => {
              assertOwner(database);
              const deleted = database.prepare(
                "DELETE FROM claims WHERE key = ? AND owner_token = ?",
              ).run(key, claimed.token);
              if (deleted.changes !== 1) throw negativeAdmissionOwnerFenced();
            }));
            released = true;
          };
          const publish = async ({ httpStatus, rejectionClass }) => {
            if (![400, 422].includes(httpStatus)) {
              throw new Error("negative admission publishes only HTTP 400 or 422");
            }
            if (rejectionClass !== "DETERMINISTIC_REQUEST_REJECTED") {
              throw new Error("negative admission rejection class is invalid");
            }
            const createdAt = nowFunction();
            const core = {
              ...identity,
              key,
              http_status: httpStatus,
              rejection_class: rejectionClass,
              cost_policy_version: COST_POLICY_VERSION,
              created_at_ms: createdAt,
              expires_at_ms: createdAt + ttlMs,
            };
            const record = {
              ...core,
              integrity_hash: sha256(stableJson(core)),
            };
            const recordJson = JSON.stringify(record);
            if (Buffer.byteLength(recordJson, "utf8") > MAX_NEGATIVE_ADMISSION_BYTES) {
              throw new Error("negative admission record exceeds its bounded size");
            }
            withDatabase((database) => immediate(database, () => {
              assertOwner(database);
              database.prepare(
                "INSERT INTO records (key, record_json, expires_at_ms) VALUES (?, ?, ?) " +
                  "ON CONFLICT(key) DO UPDATE SET record_json = excluded.record_json, " +
                  "expires_at_ms = excluded.expires_at_ms",
              ).run(key, recordJson, record.expires_at_ms);
            }));
            return Object.freeze(record);
          };
          return Object.freeze({ kind: "OWNER", key, publish, release });
        }
        if (waitNowFunction() >= deadline) throw negativeAdmissionWaitTimeout();
        await asyncDelay(5);
      }
    },
  });
}

function normalizedList(value, field, { required = false } = {}) {
  if (value === undefined || value === null) {
    if (required) throw new Error(`${field} is required`);
    return [];
  }
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`${field} must be an array of strings`);
  }
  const result = value.map((item) => item.trim()).filter(Boolean);
  if (required && result.length === 0) throw new Error(`${field} must not be empty`);
  return result;
}

function isExactLocalContract(routeConstraints) {
  return (
    routeConstraints?.allowedRoutes?.length === 1 &&
    routeConstraints.allowedRoutes[0] === "LOCAL" &&
    routeConstraints.privacyClass === "LOCAL_ONLY"
  );
}

function isLocalExecutionContract(routeConstraints, mode) {
  const routes = routeConstraints?.allowedRoutes ?? [];
  if (mode !== "READ_ONLY" || !routes.includes("LOCAL")) return false;
  return routeConstraints.privacyClass === "LOCAL_ONLY" ||
    (routes.length === 1 && routes[0] === "LOCAL");
}

function normalizeLocalAssertions(value, commandsTests, exactLocal) {
  // `pattern` is retained for wire compatibility but is always a literal substring.
  if (value === undefined) return Object.freeze([]);
  if (!exactLocal) {
    throw new Error(
      "local_assertions are allowed only for an exact LOCAL/LOCAL_ONLY contract",
    );
  }
  if (commandsTests.length === 0) {
    throw new Error("local_assertions require non-empty commands_tests");
  }
  if (!Array.isArray(value)) {
    throw new Error("local_assertions must be an array");
  }
  if (value.length > MAX_LOCAL_ASSERTIONS) {
    throw new Error(`local_assertions must contain at most ${MAX_LOCAL_ASSERTIONS} entries`);
  }
  const requiredFields = ["command_index", "stream", "pattern", "must_match"];
  const assertions = value.map((assertion, index) => {
    const label = `local_assertions[${index}]`;
    if (!assertion || typeof assertion !== "object" || Array.isArray(assertion)) {
      throw new Error(`${label} must be an object`);
    }
    const keys = Object.keys(assertion);
    const unsupported = keys.filter((key) => !requiredFields.includes(key));
    if (unsupported.length > 0) {
      throw new Error(`${label} contains an unsupported field: ${unsupported[0]}`);
    }
    const missing = requiredFields.filter((key) => !keys.includes(key));
    if (missing.length > 0) throw new Error(`${label}.${missing[0]} is required`);
    if (
      !Number.isInteger(assertion.command_index) ||
      assertion.command_index < 0 ||
      assertion.command_index >= commandsTests.length
    ) {
      throw new Error(`${label}.command_index must identify a commands_tests entry`);
    }
    if (!["stdout", "stderr"].includes(assertion.stream)) {
      throw new Error(`${label}.stream must be stdout or stderr`);
    }
    if (
      typeof assertion.pattern !== "string" ||
      assertion.pattern.trim().length === 0 ||
      assertion.pattern.length > MAX_LOCAL_ASSERTION_PATTERN_CHARS
    ) {
      throw new Error(
        `${label}.pattern must be a non-empty string of at most ` +
        `${MAX_LOCAL_ASSERTION_PATTERN_CHARS} characters`,
      );
    }
    if (typeof assertion.must_match !== "boolean") {
      throw new Error(`${label}.must_match must be a boolean`);
    }
    return Object.freeze({
      command_index: assertion.command_index,
      stream: assertion.stream,
      pattern: assertion.pattern,
      must_match: assertion.must_match,
    });
  });
  return Object.freeze(assertions);
}

function writeVerificationPathIdentity(relativePath) {
  const normalized = path.normalize(relativePath);
  return process.platform === "win32" ? normalized.toLowerCase() : normalized;
}

function writeVerificationData(value, label) {
  let prototype;
  let descriptors;
  try {
    prototype = Object.getPrototypeOf(value);
    descriptors = Object.getOwnPropertyDescriptors(value);
  } catch {
    throw new Error(`${label} must be plain data`);
  }
  if (![Object.prototype, null].includes(prototype)) {
    throw new Error(`${label} must be a plain data object`);
  }
  const data = {};
  for (const key of Reflect.ownKeys(descriptors)) {
    if (typeof key !== "string") throw new Error(`${label} contains an unsupported field`);
    const descriptor = descriptors[key];
    if (!Object.hasOwn(descriptor, "value")) {
      throw new Error(`${label} accessors are not allowed`);
    }
    data[key] = descriptor.value;
  }
  return data;
}

function normalizeWriteVerifications(value, workspace, allowedPaths, mode) {
  if (value === undefined) return Object.freeze([]);
  if (mode !== "WRITE") {
    throw new Error("write_verifications are allowed only in WRITE mode");
  }
  if (!Array.isArray(value)) throw new Error("write_verifications must be an array");
  if (value.length > MAX_WRITE_VERIFICATIONS) {
    throw new Error("LOCAL exact-byte WRITE requires exactly one write_verifications entry");
  }
  const identities = new Set();
  const requiredFields = ["path", "sha256", "byte_length", "content_base64"];
  const verifications = value.map((verification, index) => {
    const label = `write_verifications[${index}]`;
    if (!verification || typeof verification !== "object" || Array.isArray(verification)) {
      throw new Error(`${label} must be an object`);
    }
    const data = writeVerificationData(verification, label);
    const keys = Object.keys(data);
    const unsupported = keys.filter((key) => !requiredFields.includes(key));
    if (unsupported.length > 0) {
      throw new Error(`${label} contains an unsupported field: ${unsupported[0]}`);
    }
    const missing = requiredFields.filter((key) => !keys.includes(key));
    if (missing.length > 0) throw new Error(`${label}.${missing[0]} is required`);
    if (typeof data.path !== "string" || data.path.trim().length === 0) {
      throw new Error(`${label}.path must be a non-empty string`);
    }
    const relativePath = normalizeAllowedPath(workspace, data.path);
    const fullPath = path.resolve(workspace, relativePath);
    const allowed = allowedPaths.some((allowedPath) =>
      isWithin(path.resolve(workspace, allowedPath), fullPath),
    );
    if (!allowed) {
      throw new Error(`${label}.path is outside allowed_paths: ${relativePath}`);
    }
    const identity = writeVerificationPathIdentity(relativePath);
    if (identities.has(identity)) {
      throw new Error("write_verifications paths must be unique by filesystem identity");
    }
    identities.add(identity);
    if (
      typeof data.sha256 !== "string" ||
      !/^[a-f0-9]{64}$/.test(data.sha256)
    ) {
      throw new Error(`${label}.sha256 must be a lowercase 64-character SHA-256 hex string`);
    }
    if (
      !Number.isSafeInteger(data.byte_length) ||
      data.byte_length < 0 ||
      data.byte_length > MAX_WRITE_VERIFICATION_BYTES
    ) {
      throw new Error(
        `${label}.byte_length must be a nonnegative safe integer no greater than ` +
        `${MAX_WRITE_VERIFICATION_BYTES}`,
      );
    }
    if (
      typeof data.content_base64 !== "string" ||
      data.content_base64.length > MAX_LOCAL_EXACT_WRITE_BASE64_CHARS
    ) {
      throw new Error(
        `${label}.content_base64 is required and must encode at most ` +
        `${MAX_WRITE_VERIFICATION_BYTES} bytes`,
      );
    }
    const payload = Buffer.from(data.content_base64, "base64");
    if (payload.toString("base64") !== data.content_base64) {
      throw new Error(`${label}.content_base64 must be canonical base64`);
    }
    if (payload.length !== data.byte_length) {
      throw new Error(`${label} payload length does not match byte_length`);
    }
    if (sha256(payload) !== data.sha256) {
      throw new Error(`${label} payload SHA-256 does not match sha256`);
    }
    if (pathContainsReparsePoint(workspace, fullPath)) {
      throw new Error(`${label}.path contains a reparse point`);
    }
    if (!existsSync(fullPath)) {
      throw new Error(`${label}.path must identify an existing regular file`);
    }
    const targetStat = lstatSync(fullPath);
    if (!targetStat.isFile() || targetStat.isSymbolicLink()) {
      throw new Error(`${label}.path must identify a regular file`);
    }
    if (targetStat.nlink !== 1) {
      throw new Error(`${label}.path must not identify a hard-linked file`);
    }
    if (!isWithin(realpathSync.native(workspace), realpathSync.native(fullPath))) {
      throw new Error(`${label}.path resolves outside the workspace`);
    }
    return Object.freeze({
      path: relativePath,
      sha256: data.sha256,
      byte_length: data.byte_length,
      content_base64: data.content_base64,
    });
  });
  return Object.freeze(verifications);
}

function frozenArtifactDescriptors(artifacts = []) {
  return Object.freeze(artifacts.map((artifact) => Object.freeze({
    artifact_id: artifact.artifact_id,
    path: artifact.path,
    sha256: artifact.sha256,
    byte_length: artifact.byte_length,
  })));
}

function frozenArtifactPayloadIdentity(artifacts = []) {
  return canonicalHash(artifacts.map((artifact) => ({
    artifact_id: artifact.artifact_id,
    path: artifact.path,
    sha256: artifact.sha256,
    byte_length: artifact.byte_length,
    content_base64: artifact.content_base64,
  })));
}

function decodeFrozenArtifactPayload(artifact, label = "frozen artifact") {
  if (
    typeof artifact.content_base64 !== "string" ||
    artifact.content_base64.length > MAX_FROZEN_ARTIFACT_BASE64_CHARS
  ) {
    throw new Error(
      `${label}.content_base64 must be canonical base64 for at most ` +
        `${MAX_FROZEN_ARTIFACT_BYTES} bytes`,
    );
  }
  const payload = Buffer.from(artifact.content_base64, "base64");
  if (payload.toString("base64") !== artifact.content_base64) {
    throw new Error(`${label}.content_base64 must be canonical base64`);
  }
  if (payload.length !== artifact.byte_length) {
    throw new Error(`${label} payload length does not match byte_length`);
  }
  if (sha256(payload) !== artifact.sha256) {
    throw new Error(`${label} payload SHA-256 does not match sha256`);
  }
  return payload;
}

function normalizeFrozenArtifacts(
  value,
  workspace,
  allowedPaths,
  { mode, boundedFlashWrite },
) {
  if (value === undefined) return Object.freeze([]);
  if (mode !== "WRITE" || boundedFlashWrite !== true) {
    throw new Error("frozen_artifacts are allowed only for bounded Flash WRITE");
  }
  if (!Array.isArray(value)) throw new Error("frozen_artifacts must be an array");
  if (value.length > MAX_FROZEN_ARTIFACTS) {
    throw new Error(`frozen_artifacts must contain at most ${MAX_FROZEN_ARTIFACTS} entries`);
  }
  const requiredFields = [
    "artifact_id",
    "path",
    "sha256",
    "byte_length",
    "content_base64",
  ];
  const artifactIds = new Set();
  const pathIdentities = new Set();
  let declaredTotalBytes = 0;
  const artifacts = value.map((artifact, index) => {
    const label = `frozen_artifacts[${index}]`;
    if (!artifact || typeof artifact !== "object" || Array.isArray(artifact)) {
      throw new Error(`${label} must be an object`);
    }
    const data = writeVerificationData(artifact, label);
    const keys = Object.keys(data);
    const unsupported = keys.filter((key) => !requiredFields.includes(key));
    if (unsupported.length > 0) {
      throw new Error(`${label} contains an unsupported field: ${unsupported[0]}`);
    }
    const missing = requiredFields.filter((key) => !keys.includes(key));
    if (missing.length > 0) throw new Error(`${label}.${missing[0]} is required`);
    if (
      typeof data.artifact_id !== "string" ||
      !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(data.artifact_id)
    ) {
      throw new Error(
        `${label}.artifact_id must contain 1-128 safe identifier characters`,
      );
    }
    if (artifactIds.has(data.artifact_id)) {
      throw new Error("frozen_artifacts artifact_id values must be unique");
    }
    artifactIds.add(data.artifact_id);
    if (typeof data.path !== "string" || data.path.trim().length === 0) {
      throw new Error(`${label}.path must be a non-empty string`);
    }
    const relativePath = normalizeAllowedPath(workspace, data.path);
    const fullPath = path.resolve(workspace, relativePath);
    if (!allowedPaths.some((allowed) =>
      isWithin(path.resolve(workspace, allowed), fullPath))) {
      throw new Error(`${label}.path is outside allowed_paths: ${relativePath}`);
    }
    const pathIdentity = writeVerificationPathIdentity(relativePath);
    if (pathIdentities.has(pathIdentity)) {
      throw new Error("frozen_artifacts paths must be unique by filesystem identity");
    }
    pathIdentities.add(pathIdentity);
    if (
      typeof data.sha256 !== "string" ||
      !/^[a-f0-9]{64}$/.test(data.sha256)
    ) {
      throw new Error(
        `${label}.sha256 must be a lowercase 64-character SHA-256 hex string`,
      );
    }
    if (
      !Number.isSafeInteger(data.byte_length) ||
      data.byte_length < 0 ||
      data.byte_length > MAX_FROZEN_ARTIFACT_BYTES
    ) {
      throw new Error(
        `${label}.byte_length must be a nonnegative safe integer no greater than ` +
          `${MAX_FROZEN_ARTIFACT_BYTES}`,
      );
    }
    declaredTotalBytes += data.byte_length;
    if (declaredTotalBytes > MAX_FROZEN_ARTIFACT_TOTAL_BYTES) {
      throw new Error(
        `frozen_artifacts declared bytes exceed ${MAX_FROZEN_ARTIFACT_TOTAL_BYTES}`,
      );
    }
    if (pathContainsReparsePoint(workspace, fullPath)) {
      throw new Error(`${label}.path contains a reparse point`);
    }
    if (existsSync(fullPath)) {
      const metadata = lstatSync(fullPath);
      if (!metadata.isFile() || metadata.isSymbolicLink()) {
        throw new Error(`${label}.path must identify a regular file or new file target`);
      }
      if (metadata.nlink !== 1) {
        throw new Error(`${label}.path must not identify a hard-linked file`);
      }
      if (!isWithin(realpathSync.native(workspace), realpathSync.native(fullPath))) {
        throw new Error(`${label}.path resolves outside the workspace`);
      }
    }
    const normalized = Object.freeze({
      artifact_id: data.artifact_id,
      path: relativePath,
      sha256: data.sha256,
      byte_length: data.byte_length,
      content_base64: data.content_base64,
    });
    decodeFrozenArtifactPayload(normalized, label);
    return normalized;
  });
  return Object.freeze(artifacts);
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function portablePath(value) {
  return value.replaceAll("\\", "/").replace(/^\.\//, "").replace(/\/$/, "");
}

function normalizeAllowedPath(workspace, value) {
  if (!value) throw new Error("allowed_paths and required_reads.path entries must not be empty");
  if (path.isAbsolute(value)) {
    throw new Error(
      `allowed_paths and required_reads.path entries must be workspace-relative: ${value}`,
    );
  }
  const portable = portablePath(value);
  const resolved = path.resolve(workspace, portable);
  if (!isWithin(workspace, resolved)) throw new Error(`allowed path is outside workspace: ${value}`);
  if (CREDENTIAL_PATTERN.test(portable)) throw new Error(`credential path is forbidden: ${value}`);
  return portable;
}

function assertProviderCommandSafety(command, mode) {
  if (ALWAYS_FORBIDDEN_COMMAND.test(command)) {
    throw new Error("mutating command is forbidden");
  }
  if (mode === "READ_ONLY" && READ_ONLY_WRITE_COMMAND.test(command)) {
    throw new Error("mutating command is forbidden in READ_ONLY mode");
  }
}

function localCommandOperand(command) {
  if (/[\r\n`;&|<>$]/.test(command)) {
    throw new Error("LOCAL command contains a forbidden shell metacharacter");
  }
  const forms = [
    ["GET_CONTENT", /^Get-Content -LiteralPath (.+)$/],
    ["GET_FILE_HASH_SHA256", /^Get-FileHash -Algorithm SHA256 -LiteralPath (.+)$/],
    ["NODE_CHECK", /^node --check (.+)$/],
  ];
  const selected = forms
    .map(([kind, pattern]) => [kind, command.match(pattern)])
    .find(([, matched]) => matched);
  if (!selected) throw new Error("command is outside the strict LOCAL command allowlist");
  const [kind, matched] = selected;
  let operand = matched[1].trim();
  if (
    operand.length >= 2 &&
    operand[0] === operand.at(-1) &&
    ["'", "\""].includes(operand[0])
  ) {
    operand = operand.slice(1, -1);
  } else if (/\s/.test(operand)) {
    throw new Error("LOCAL command path with spaces must be quoted");
  }
  if (!operand || /["']/.test(operand)) {
    throw new Error("LOCAL command path quoting is invalid");
  }
  return { kind, operand };
}

function normalizeLocalCommandSpecs(commands, workspace, allowedPaths, localExecution, mode) {
  if (!localExecution) return Object.freeze([]);
  if (commands.length === 0) {
    throw new Error("exact LOCAL contracts require non-empty commands_tests");
  }
  if (commands.length > MAX_LOCAL_COMMANDS) {
    throw new Error(`commands_tests must contain at most ${MAX_LOCAL_COMMANDS} commands`);
  }
  const allowedRoots = allowedPaths.map((allowed) => path.resolve(workspace, allowed));
  return Object.freeze(commands.map((command) => {
    if (command.length > MAX_LOCAL_COMMAND_CHARS) {
      throw new Error(
        `LOCAL command must contain at most ${MAX_LOCAL_COMMAND_CHARS} characters`,
      );
    }
    assertProviderCommandSafety(command, mode);
    const { kind, operand } = localCommandOperand(command);
    const portable = normalizeAllowedPath(workspace, operand);
    const target = path.resolve(workspace, portable);
    if (!allowedRoots.some((allowed) => isWithin(allowed, target))) {
      throw new Error(`LOCAL command dependency is outside allowed_paths: ${portable}`);
    }
    return Object.freeze({ kind, path: portable });
  }));
}

function localFileIdentity(stat) {
  return {
    dev: String(stat.dev),
    ino: String(stat.ino),
    size: String(stat.size),
    mode: String(stat.mode),
    mtime_ns: String(stat.mtimeNs),
    ctime_ns: String(stat.ctimeNs),
  };
}

function sameLocalFileIdentity(left, right) {
  return stableJson(localFileIdentity(left)) === stableJson(localFileIdentity(right));
}

function assertLocalDependencyAllowed(task, relativePath, realTarget) {
  const lexicalTarget = path.resolve(task.workspace, relativePath);
  const lexicalAllowed = task.allowedPaths
    .map((allowed) => path.resolve(task.workspace, allowed))
    .filter((allowed) => isWithin(allowed, lexicalTarget));
  if (lexicalAllowed.length === 0) {
    throw new Error(`LOCAL command dependency is outside allowed_paths: ${relativePath}`);
  }
  const realAllowed = lexicalAllowed.map((allowed) => {
    const stat = lstatSync(allowed, { bigint: true });
    if (stat.isSymbolicLink()) {
      throw new Error(`LOCAL allowed_paths contains a symlink or reparse point: ${relativePath}`);
    }
    return realpathSync(allowed);
  });
  if (!realAllowed.some((allowed) => isWithin(allowed, realTarget))) {
    throw new Error(`LOCAL command dependency is outside allowed_paths: ${relativePath}`);
  }
}

function captureLocalRegularFile(task, relativePath) {
  const target = path.resolve(task.workspace, relativePath);
  let descriptor;
  try {
    const beforePath = lstatSync(target, { bigint: true });
    if (beforePath.isSymbolicLink() || !beforePath.isFile()) {
      throw new Error(`LOCAL command dependency is not a regular file: ${relativePath}`);
    }
    if (beforePath.dev === 0n && beforePath.ino === 0n) {
      throw new Error(`LOCAL dependency identity is unavailable: ${relativePath}`);
    }
    const beforeRealPath = realpathSync(target);
    if (!isWithin(task.workspace, beforeRealPath)) {
      throw new Error(`LOCAL command dependency is outside workspace: ${relativePath}`);
    }
    assertLocalDependencyAllowed(task, relativePath, beforeRealPath);

    descriptor = openSync(target, "r");
    const beforeHandle = fstatSync(descriptor, { bigint: true });
    if (!beforeHandle.isFile() || !sameLocalFileIdentity(beforePath, beforeHandle)) {
      throw new Error(`LOCAL dependency identity changed before capture: ${relativePath}`);
    }
    if (beforeHandle.size > BigInt(MAX_READ_FILE_BYTES)) {
      throw new Error(`LOCAL command dependency exceeds bounded size: ${relativePath}`);
    }
    const bytes = readFileSync(descriptor);
    const afterHandle = fstatSync(descriptor, { bigint: true });
    if (!sameLocalFileIdentity(beforeHandle, afterHandle)) {
      throw new Error(`LOCAL dependency changed during capture: ${relativePath}`);
    }
    const afterPath = lstatSync(target, { bigint: true });
    if (
      afterPath.isSymbolicLink() ||
      !afterPath.isFile() ||
      !sameLocalFileIdentity(afterHandle, afterPath)
    ) {
      throw new Error(`LOCAL dependency path changed during capture: ${relativePath}`);
    }
    const afterRealPath = realpathSync(target);
    if (afterRealPath !== beforeRealPath || !isWithin(task.workspace, afterRealPath)) {
      throw new Error(`LOCAL dependency containment changed during capture: ${relativePath}`);
    }
    assertLocalDependencyAllowed(task, relativePath, afterRealPath);
    return Object.freeze({
      path: relativePath,
      bytes,
      sha256: sha256(bytes),
      byteLength: bytes.length,
    });
  } catch (error) {
    if (
      /LOCAL (?:command dependency|dependency)/i.test(String(error?.message ?? "")) ||
      /allowed_paths/i.test(String(error?.message ?? ""))
    ) {
      throw error;
    }
    throw new Error(
      `LOCAL dependency capture failed for ${relativePath}: ${error?.message ?? String(error)}`,
    );
  } finally {
    if (descriptor !== undefined) closeSync(descriptor);
  }
}

function nodePackageContextPath(task, commandPath) {
  if (path.extname(commandPath).toLowerCase() !== ".js") return null;
  let directory = path.dirname(path.resolve(task.workspace, commandPath));
  const filesystemRoot = path.parse(directory).root;
  while (true) {
    const candidate = path.join(directory, "package.json");
    if (existsSync(candidate)) {
      if (!isWithin(task.workspace, candidate)) {
        throw new Error("LOCAL node --check package context is outside the workspace");
      }
      const relative = portablePath(path.relative(task.workspace, candidate));
      const lexicalTarget = path.resolve(task.workspace, relative);
      if (
        !task.allowedPaths.some((allowed) =>
          isWithin(path.resolve(task.workspace, allowed), lexicalTarget)
        )
      ) {
        throw new Error(
          `LOCAL node --check requires declared package context in allowed_paths: ${relative}`,
        );
      }
      return relative;
    }
    if (directory === filesystemRoot) return null;
    directory = path.dirname(directory);
  }
}

function localNodeModuleType(spec, packageCapture) {
  const extension = path.extname(spec.path).toLowerCase();
  if (extension === ".mjs") return "module";
  if (extension !== ".js") return "commonjs";
  if (!packageCapture) return "commonjs";
  let parsed;
  try {
    parsed = JSON.parse(packageCapture.bytes.toString("utf8"));
  } catch {
    throw new Error(`LOCAL node --check package context is invalid: ${packageCapture.path}`);
  }
  return parsed?.type === "module" ? "module" : "commonjs";
}

function captureLocalDependencies(task, snapshotRoot) {
  if (!Array.isArray(task.localCommandSpecs) || task.localCommandSpecs.length === 0) {
    return null;
  }
  mkdirSync(snapshotRoot, { recursive: false, mode: 0o700 });
  const rolesByPath = new Map();
  const packageContexts = task.localCommandSpecs.map((spec) =>
    spec.kind === "NODE_CHECK" ? nodePackageContextPath(task, spec.path) : null
  );
  for (const spec of task.localCommandSpecs) {
    const roles = rolesByPath.get(spec.path) ?? new Set();
    roles.add("COMMAND");
    rolesByPath.set(spec.path, roles);
  }
  for (const packagePath of packageContexts.filter(Boolean)) {
    const roles = rolesByPath.get(packagePath) ?? new Set();
    roles.add("NODE_PACKAGE_CONTEXT");
    rolesByPath.set(packagePath, roles);
  }

  const captures = new Map();
  for (const relativePath of [...rolesByPath.keys()].sort()) {
    captures.set(relativePath, captureLocalRegularFile(task, relativePath));
  }
  const confirmedContexts = task.localCommandSpecs.map((spec) =>
    spec.kind === "NODE_CHECK" ? nodePackageContextPath(task, spec.path) : null
  );
  if (stableJson(packageContexts) !== stableJson(confirmedContexts)) {
    throw new Error("LOCAL node --check package context changed during capture");
  }

  const commandSnapshots = task.localCommandSpecs.map((spec, index) => {
    const capture = captures.get(spec.path);
    const commandDirectory = path.join(snapshotRoot, String(index).padStart(2, "0"));
    mkdirSync(commandDirectory, { recursive: false, mode: 0o700 });
    const extension = path.extname(spec.path);
    const snapshotPath = path.join(commandDirectory, `dependency${extension}`);
    writeFileSync(snapshotPath, capture.bytes, { flag: "wx", mode: 0o400 });
    chmodSync(snapshotPath, 0o400);
    const nodeModuleType = spec.kind === "NODE_CHECK"
      ? localNodeModuleType(
          spec,
          packageContexts[index] ? captures.get(packageContexts[index]) : null,
        )
      : null;
    const verificationPaths = [Object.freeze({
      path: snapshotPath,
      sha256: capture.sha256,
    })];
    if (nodeModuleType) {
      const contextPath = path.join(commandDirectory, "package.json");
      const contextBytes = Buffer.from(`${JSON.stringify({ type: nodeModuleType })}\n`, "utf8");
      writeFileSync(contextPath, contextBytes, { flag: "wx", mode: 0o400 });
      chmodSync(contextPath, 0o400);
      verificationPaths.push(Object.freeze({
        path: contextPath,
        sha256: sha256(contextBytes),
      }));
    }
    return Object.freeze({
      snapshotPath,
      snapshotContent: Buffer.from(capture.bytes),
      capturedSha256: capture.sha256,
      nodeModuleType,
      verificationPaths: Object.freeze(verificationPaths),
    });
  });
  const identity = Object.freeze(
    [...captures.entries()].map(([relativePath, capture]) => Object.freeze({
      path: relativePath,
      sha256: capture.sha256,
      bytes: capture.byteLength,
      roles: Object.freeze([...rolesByPath.get(relativePath)].sort()),
    })),
  );
  return Object.freeze({
    identity,
    commandSnapshots: Object.freeze(commandSnapshots),
    fingerprint: canonicalHash(identity),
    snapshotRoot,
  });
}

function verifyLocalCommandSnapshot(snapshot) {
  for (const expected of snapshot.verificationPaths) {
    const stat = lstatSync(expected.path, { bigint: true });
    if (stat.isSymbolicLink() || !stat.isFile()) {
      throw new Error("LOCAL immutable snapshot is not a regular file");
    }
    if (sha256(readFileSync(expected.path)) !== expected.sha256) {
      throw new Error("LOCAL immutable snapshot identity changed");
    }
  }
}

export function validateSubmission(
  raw,
  mode,
  profile = resolvePrimaryProfile(),
  { codexOrchestrationEnabled = resolveCodexOrchestrationEnabled() } = {},
) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("submission must be an object");
  }
  if (!new Set(["READ_ONLY", "WRITE"]).has(mode)) throw new Error(`unknown mode: ${mode}`);
  if (raw.require_cache !== undefined && typeof raw.require_cache !== "boolean") {
    throw new Error("require_cache must be a boolean");
  }
  if (raw.require_cache === true && mode !== "READ_ONLY") {
    throw new Error("require_cache is allowed only for READ_ONLY jobs");
  }
  if (raw.require_cache === true && raw.reuse_cache === false) {
    throw new Error("require_cache=true is incompatible with reuse_cache=false");
  }
  const fastOnly = (() => {
    const value = process.env.DEEPLUNA_FAST_ONLY;
    if (value === undefined || value === "" || value === "0") return false;
    if (value === "1") return true;
    throw new Error("DEEPLUNA_FAST_ONLY must be unset, 0, or exactly 1");
  })();
  if (fastOnly && profile.id !== "deepinfra-fast") {
    throw new Error("Fast-only worker mode requires the deepinfra-fast primary profile");
  }
  const objective = String(raw.objective ?? "").trim();
  if (!objective) throw new Error("objective is required");
  if (objective.length > 12_000) throw new Error("objective exceeds 12000 characters");
  const tier = String(
    raw.tier ?? (fastOnly ? "FLASH" : mode === "WRITE" ? "PRO" : "FLASH"),
  ).toUpperCase();
  if (!(tier in profile.models)) throw new Error(`unknown tier: ${tier}`);
  if (fastOnly && tier !== "FLASH") {
    throw new Error("Fast-only worker mode requires tier FLASH");
  }
  if (mode === "WRITE" && !["PRO", "REASONING", "FLASH"].includes(tier)) {
    throw new Error(
      "WRITE jobs require PRO, REASONING, or the bounded explicit FLASH contract",
    );
  }
  const boundedFlashWrite = mode === "WRITE" && tier === "FLASH";
  const requiredReadsRequested = Array.isArray(raw.required_reads) && raw.required_reads.length > 0;
  if (
    raw.route_constraints !== undefined &&
    (!raw.route_constraints ||
      typeof raw.route_constraints !== "object" ||
      Array.isArray(raw.route_constraints))
  ) {
    throw new Error("route_constraints must be an object");
  }
  const defaultRoutes = fastOnly
    ? ["LOCAL", "FLASH"]
    : tier === "FLASH"
    ? ["LOCAL", "FLASH", ...(codexOrchestrationEnabled ? ["LUNA"] : [])]
    : ["LOCAL", isDeepInfraProfile(profile.id)
      ? tier === "REASONING" ? "NEMOTRON" : "V4_PRO"
      : "DIRECT_PRO",
      ...(codexOrchestrationEnabled ? ["LUNA"] : [])];
  const evidenceSafeRoutes = requiredReadsRequested
    ? defaultRoutes.filter((route) => !["LUNA", "GLM"].includes(route))
    : defaultRoutes;
  if (requiredReadsRequested && evidenceSafeRoutes.length === 0) {
    evidenceSafeRoutes.push("LOCAL");
  }
  let routeConstraints = normalizeRouteConstraints(raw.route_constraints ?? {
    allowed_routes: requiredReadsRequested ? evidenceSafeRoutes : defaultRoutes,
    fallback_policy: fastOnly
      ? "NO_LUNA"
      : requiredReadsRequested
      ? "NO_LUNA"
      : (codexOrchestrationEnabled ? "LUNA_ELIGIBLE" : "NO_LUNA"),
    maximum_attempts: fastOnly ? 1 : codexOrchestrationEnabled ? 2 : 1,
    maximum_estimated_cost_usd: 1,
    privacy_class: "PROVIDER_ALLOWED",
  });
  if (
    fastOnly &&
    (
      routeConstraints.allowedRoutes.some((route) => !["LOCAL", "FLASH"].includes(route)) ||
      routeConstraints.fallbackPolicy !== "NO_LUNA" ||
      routeConstraints.maximumAttempts !== 1
    )
  ) {
    throw new Error(
      "Fast-only worker mode permits only LOCAL and FLASH routes, NO_LUNA, and one attempt",
    );
  }
  if (
    routeConstraints.allowedRoutes.length === 1 &&
    routeConstraints.allowedRoutes[0] === "GLM" &&
    routeConstraints.maximumProviderCalls !== 1
  ) {
    throw new Error("GLM-5.2 requires exactly one provider call");
  }
  if (
    routeConstraints.fallbackPolicy === "NO_LUNA" &&
    routeConstraints.allowedRoutes.every((route) => ["LUNA", "GLM"].includes(route))
  ) {
    throw new Error("NO_LUNA with Luna-only allowed routes is invalid.");
  }

  const requestedWorkspace = path.resolve(String(raw.workspace ?? process.cwd()));
  if (!existsSync(requestedWorkspace) || !statSync(requestedWorkspace).isDirectory()) {
    throw new Error(`workspace is not a directory: ${requestedWorkspace}`);
  }
  const workspace = realpathSync(requestedWorkspace);
  const allowedRoot = process.env.DEEPSEEK_ALLOWED_ROOT;
  if (allowedRoot && !isWithin(realpathSync(path.resolve(allowedRoot)), workspace)) {
    throw new Error(`workspace is outside configured root: ${workspace}`);
  }

  const allowedPaths = normalizedList(raw.allowed_paths, "allowed_paths").map((item) =>
    normalizeAllowedPath(workspace, item),
  );
  if (mode === "WRITE" && allowedPaths.length === 0) {
    throw new Error("WRITE jobs require allowed_paths");
  }
  if (mode === "WRITE") {
    for (const relative of allowedPaths) {
      const fullPath = path.resolve(workspace, relative);
      if (
        existsSync(fullPath) &&
        (
          pathContainsReparsePoint(workspace, fullPath) ||
          (
            lstatSync(fullPath).isFile() &&
            lstatSync(fullPath).nlink !== 1
          )
        )
      ) {
        throw new Error(
          `WRITE allowed path must not be a reparse point or hard-linked file: ${relative}`,
        );
      }
    }
  }
  const commandsTests = normalizedList(raw.commands_tests, "commands_tests");
  if (mode === "WRITE" && commandsTests.length > MAX_LOCAL_COMMANDS) {
    throw new Error(`WRITE commands_tests must contain at most ${MAX_LOCAL_COMMANDS} commands`);
  }
  if (
    mode === "WRITE" &&
    commandsTests.some((command) => command.length > MAX_LOCAL_COMMAND_CHARS)
  ) {
    throw new Error(
      `WRITE commands_tests entries must not exceed ${MAX_LOCAL_COMMAND_CHARS} characters`,
    );
  }
  const exactLocal = isExactLocalContract(routeConstraints);
  const localExecution = isLocalExecutionContract(routeConstraints, mode);
  const localCommandSpecs = normalizeLocalCommandSpecs(
    commandsTests,
    workspace,
    allowedPaths,
    localExecution,
    mode,
  );
  const localAssertions = normalizeLocalAssertions(
    raw.local_assertions,
    commandsTests,
    exactLocal,
  );
  const writeVerifications = normalizeWriteVerifications(
    raw.write_verifications,
    workspace,
    allowedPaths,
    mode,
  );
  const frozenArtifacts = normalizeFrozenArtifacts(
    raw.frozen_artifacts,
    workspace,
    allowedPaths,
    { mode, boundedFlashWrite },
  );
  const frozenArtifactIdentity = frozenArtifactPayloadIdentity(frozenArtifacts);
  const localExactWrite = mode === "WRITE" && writeVerifications.length === 1;
  if (localExactWrite) {
    if (!exactLocal) {
      throw new Error(
        "exact-byte WRITE requires the sole LOCAL route with privacy_class LOCAL_ONLY",
      );
    }
    if (routeConstraints.fallbackPolicy !== "NO_LUNA") {
      throw new Error("exact-byte WRITE requires NO_LUNA");
    }
    if (routeConstraints.maximumAttempts !== 1) {
      throw new Error("exact-byte WRITE requires exactly one local attempt");
    }
    if (routeConstraints.maximumProviderCalls !== 1) {
      throw new Error("exact-byte WRITE requires maximum_provider_calls=1");
    }
    if (routeConstraints.maximumEstimatedCostUsd !== 0) {
      throw new Error("exact-byte WRITE requires a zero-cost route contract");
    }
    if (commandsTests.length > 0) {
      throw new Error("exact-byte WRITE excludes commands_tests");
    }
    if (localAssertions.length > 0) {
      throw new Error("exact-byte WRITE excludes local_assertions");
    }
    if (raw.reuse_cache === true) {
      throw new Error("exact-byte WRITE does not permit cache reuse");
    }
    if (
      allowedPaths.length !== 1 ||
      writeVerificationPathIdentity(allowedPaths[0]) !==
        writeVerificationPathIdentity(writeVerifications[0].path)
    ) {
      throw new Error("exact-byte WRITE allowed_paths must contain only its target file");
    }
  }
  const evidenceContract = normalizeEvidenceContract(raw, {
    normalizePath: (value) => normalizeAllowedPath(workspace, value),
    isAllowedPath: (relative) => {
      if (mode === "WRITE") return true;
      const target = path.resolve(workspace, relative);
      return allowedPaths.some((allowed) => isWithin(path.resolve(workspace, allowed), target));
    },
  });
  let routeNormalization = null;
  const explicitProviderCallCap =
    raw.route_constraints !== undefined &&
    Object.hasOwn(raw.route_constraints, "maximum_provider_calls");
  const flashPackedNormalizationEligible =
    explicitProviderCallCap &&
    mode === "READ_ONLY" &&
    tier === "FLASH" &&
    evidenceContract.requiredReads.length > 0 &&
    routeConstraints.allowedRoutes.includes("FLASH") &&
    routeConstraints.allowedRoutes.every((route) => ["LOCAL", "FLASH"].includes(route)) &&
    routeConstraints.fallbackPolicy === "NO_LUNA" &&
    routeConstraints.maximumAttempts === 1 &&
    routeConstraints.privacyClass === "PROVIDER_ALLOWED" &&
    commandsTests.length === 0;
  if (
    flashPackedNormalizationEligible &&
    (
      routeConstraints.maximumProviderCalls !== 1 ||
      routeConstraints.allowedRoutes.length !== 1
    )
  ) {
    routeNormalization = Object.freeze({
      reason: "FLASH_PACKED_ONE_CALL",
      requested_allowed_routes: Object.freeze([...routeConstraints.allowedRoutes]),
      requested_maximum_provider_calls: routeConstraints.maximumProviderCalls,
      effective_allowed_routes: Object.freeze(["FLASH"]),
      effective_maximum_provider_calls: 1,
    });
    routeConstraints = Object.freeze({
      ...routeConstraints,
      allowedRoutes: Object.freeze(["FLASH"]),
      maximumProviderCalls: 1,
    });
  }
  if (boundedFlashWrite) {
    if (
      raw.route_constraints === undefined ||
      routeConstraints.allowedRoutes.length !== 1 ||
      routeConstraints.allowedRoutes[0] !== "FLASH"
    ) {
      throw new Error(
        "Flash WRITE requires an explicit FLASH-only route contract",
      );
    }
    if (routeConstraints.fallbackPolicy !== "NO_LUNA") {
      throw new Error("Flash WRITE requires NO_LUNA");
    }
    if (routeConstraints.maximumAttempts !== 1) {
      throw new Error("Flash WRITE requires exactly one attempt");
    }
    if (routeConstraints.maximumProviderCalls !== 1) {
      throw new Error("Flash WRITE requires maximum_provider_calls=1");
    }
    if (routeConstraints.maximumEstimatedCostUsd > 0.01) {
      throw new Error("Flash WRITE cost ceiling must not exceed 0.01 USD");
    }
    if (routeConstraints.privacyClass !== "PROVIDER_ALLOWED") {
      throw new Error("Flash WRITE requires PROVIDER_ALLOWED");
    }
    if (commandsTests.length === 0) {
      throw new Error(
        "Flash WRITE requires at least one commands_tests host post-write verifier",
      );
    }
    if (evidenceContract.requiredReads.length === 0) {
      throw new Error("Flash WRITE requires non-empty required_reads");
    }
    if (evidenceContract.coverageSpec?.mode !== "ALL_REQUIRED_READS") {
      throw new Error(
        "Flash WRITE requires ALL_REQUIRED_READS citation coverage",
      );
    }
  }
  const glmPackedEvidenceMode =
    mode === "READ_ONLY" &&
    evidenceContract.requiredReads.length > 0 &&
    routeConstraints.allowedRoutes.length === 1 &&
    routeConstraints.allowedRoutes[0] === "GLM" &&
    routeConstraints.fallbackPolicy === "LUNA_ELIGIBLE";
  const flashPackedEvidenceRequested =
    mode === "READ_ONLY" &&
    tier === "FLASH" &&
    evidenceContract.requiredReads.length > 0 &&
    routeConstraints.maximumProviderCalls === 1 &&
    routeConstraints.allowedRoutes.includes("FLASH");
  const flashPackedEvidenceMode =
    flashPackedEvidenceRequested &&
    routeConstraints.allowedRoutes.length === 1 &&
    routeConstraints.allowedRoutes[0] === "FLASH" &&
    routeConstraints.fallbackPolicy === "NO_LUNA" &&
    routeConstraints.maximumAttempts === 1 &&
    routeConstraints.privacyClass === "PROVIDER_ALLOWED" &&
    commandsTests.length === 0;
  const packedEvidenceMode = glmPackedEvidenceMode
    ? GLM_PACKED_EVIDENCE_MODE
    : flashPackedEvidenceMode
      ? FLASH_PACKED_EVIDENCE_MODE
      : boundedFlashWrite
        ? FLASH_PACKED_WRITE_MODE
        : null;
  if (evidenceContract.requiredReads.length > 0) {
    if (flashPackedEvidenceRequested && (
      routeConstraints.allowedRoutes.length !== 1 ||
      routeConstraints.allowedRoutes[0] !== "FLASH" ||
      routeConstraints.fallbackPolicy !== "NO_LUNA" ||
      routeConstraints.privacyClass !== "PROVIDER_ALLOWED"
    )) {
      throw new Error(
        "Flash packed evidence requires the FLASH-only NO_LUNA PROVIDER_ALLOWED route",
      );
    }
    if (flashPackedEvidenceRequested && routeConstraints.maximumAttempts !== 1) {
      throw new Error("Flash packed evidence requires exactly one attempt");
    }
    if (flashPackedEvidenceRequested && commandsTests.length > 0) {
      throw new Error(
        "Flash packed evidence excludes commands_tests; prepack exact file ranges only",
      );
    }
    if (!packedEvidenceMode && (
      routeConstraints.fallbackPolicy !== "NO_LUNA" ||
      routeConstraints.allowedRoutes.includes("LUNA") ||
      routeConstraints.allowedRoutes.includes("GLM")
    )) {
      throw new Error(
        "required evidence coverage requires NO_LUNA and excludes fallback routes",
      );
    }
    if (glmPackedEvidenceMode && routeConstraints.maximumAttempts !== 1) {
      throw new Error("GLM packed evidence requires exactly one attempt");
    }
    if (glmPackedEvidenceMode && commandsTests.length > 0) {
      throw new Error("GLM packed evidence excludes commands_tests; prepack exact file ranges only");
    }
    for (const read of evidenceContract.requiredReads) {
      const fullPath = path.resolve(workspace, read.path);
      const metadata = existsSync(fullPath) ? lstatSync(fullPath) : null;
      const immutableRead = !allowedPaths.some((allowed) =>
        isWithin(path.resolve(workspace, allowed), fullPath),
      );
      if (
        metadata === null ||
        pathContainsReparsePoint(workspace, fullPath) ||
        !metadata.isFile() ||
        (immutableRead && metadata.nlink !== 1) ||
        !isWithin(realpathSync(workspace), realpathSync(fullPath))
      ) {
        throw new Error(`required evidence is not a regular file: ${read.path}`);
      }
    }
  }
  if (
    mode === "READ_ONLY" &&
    tier === "FLASH" &&
    allowedPaths.length > 0 &&
    evidenceContract.requiredReads.length === 0 &&
    routeConstraints.allowedRoutes.includes("FLASH") &&
    routeConstraints.maximumProviderCalls === 1
  ) {
    throw new Error(
      "One-call Flash repository reads require exact required_reads for packed evidence; " +
        "otherwise allow at least two provider calls.",
    );
  }
  if (localExactWrite && evidenceContract.requiredReads.length > 0) {
    throw new Error("exact-byte WRITE excludes required_reads");
  }
  const requiredOutput = normalizedList(raw.required_output, "required_output", { required: true });
  const definitionOfDone = normalizedList(raw.definition_of_done, "definition_of_done", {
    required: true,
  });
  const timeoutMinutes = Number(raw.timeout_minutes ?? 30);
  if (!Number.isFinite(timeoutMinutes) || timeoutMinutes < 1 || timeoutMinutes > 180) {
    throw new Error("timeout_minutes must be between 1 and 180");
  }
  const defaultOutputTokens = tier === "FLASH"
    ? Number(process.env.DEEPLUNA_FAST_MAX_OUTPUT_TOKENS ?? 4_096)
    : 4_000;
  const maxOutputTokens = Number(raw.max_output_tokens ?? defaultOutputTokens);
  const minimumOutputTokens = exactLocal
    ? MIN_LOCAL_OUTPUT_TOKENS
    : MIN_HANDOFF_OUTPUT_TOKENS;
  if (
    !Number.isInteger(maxOutputTokens) ||
    maxOutputTokens < minimumOutputTokens ||
    maxOutputTokens > 8_192
  ) {
    throw new Error(
      `max_output_tokens must be an integer between ${minimumOutputTokens} and 8192`,
    );
  }

  return Object.freeze({
    taskId: String(raw.task_id ?? "UNASSIGNED").trim() || "UNASSIGNED",
    fastOnly,
    objective,
    mode,
    tier,
    model: localExactWrite ? LOCAL_EXACT_WRITE_MODEL : profile.models[tier],
    primaryProfile: profile.id,
    primaryProvider: profile.provider,
    primaryRoute: profile.route,
    primaryDisplayName: profile.displayName,
    apiUrl: process.env.DEEPSEEK_BASE_URL
      ? process.env.DEEPSEEK_BASE_URL
      : profile.apiUrl,
    credentialEnv: profile.credentialEnv,
    requestDialect: profile.requestDialect,
    serviceTier: profile.serviceTier,
    reasoningEffort: profile.reasoning[tier],
    workspace,
    allowedPaths: [...new Set(allowedPaths)],
    requiredReads: evidenceContract.requiredReads,
    packedEvidenceMode,
    routeNormalization,
    coverageSpec: evidenceContract.coverageSpec,
    coverageStatus: evidenceContract.coverageStatus,
    coverageHash: evidenceContract.coverageHash,
    forbiddenActions: normalizedList(raw.forbidden_actions, "forbidden_actions"),
    commandsTests,
    localCommandSpecs,
    localCommandPolicyVersion: localExecution ? LOCAL_COMMAND_POLICY_VERSION : null,
    localExactWrite,
    localExactWritePolicyVersion: localExactWrite
      ? LOCAL_EXACT_WRITE_POLICY_VERSION
      : null,
    localRuntimeIdentity: localExecution || localExactWrite
      ? LOCAL_RUNTIME_IDENTITY
      : null,
    localAssertions,
    writeVerifications,
    frozenArtifacts,
    frozenArtifactPayloadIdentity: frozenArtifactIdentity,
    frozenArtifactPolicyVersion: frozenArtifacts.length > 0
      ? FROZEN_ARTIFACT_POLICY_VERSION
      : null,
    definitionOfDone,
    requiredOutput,
    timeoutMs: Math.round(timeoutMinutes * 60_000),
    maxOutputTokens,
    reuseCache: mode === "READ_ONLY" && raw.reuse_cache !== false,
    requireCache: mode === "READ_ONLY" && raw.require_cache === true,
    routeConstraints,
    fallbackPolicy: routeConstraints.fallbackPolicy,
  });
}

export function buildWorkerPrompt(task) {
  const evidenceInstructions = task.coverageSpec?.mode === "ALL_REQUIRED_READS"
    ? [
        "For every non-empty governed positive_findings or negative_findings entry, include a matching citations entry.",
        "After read_file, copy its returned evidence_id and cite an exact line range inside that receipt.",
        "Each citation must contain exactly finding_field, finding_index, evidence_id, start, end, and unit='line'; citations is mandatory even when empty.",
        "Governed findings may contain only claims supported by read_file receipts; put command outcomes in tests or summary.",
        "Use an empty findings array instead of a meta-claim such as 'no negative findings'.",
      ]
    : [];
  const system = [
    `You are a bounded ${task.primaryDisplayName ?? "repository"} worker invoked directly by Codex.`,
    "Sol is the sole head engineer and retains architecture, scientific interpretation, novelty, thesis claims, and final approval.",
    "Do not delegate, spawn nested agents, make architectural decisions, or make scientific claims.",
    "Use only the supplied tools. Never request or reveal chain-of-thought; provide concise evidence only.",
    "Do not ask whether the instruction was understood, do not restate it, and do not request confirmation.",
    "Work directly against definition_of_done in listed order; do not narrate progress.",
    "Every non-final provider turn must issue only novel, bounded tool requests that advance an unmet criterion.",
    "Batch independent reads in one turn, never repeat equivalent tool arguments, and reserve the final provider turn for finish_handoff.",
    "If one material ambiguity remains, return BLOCKED once; do not recursively critique the same answer.",
    "Stop and report BLOCKED when requirements are ambiguous or architecture_uncertainty is true.",
    task.mode === "WRITE"
      ? "A purely mechanical WRITE may return PASS with evidence_verdict=NOT_APPLICABLE and scientific_uncertainty=true; Sol still performs mandatory final acceptance."
      : "Stop and report BLOCKED when scientific_uncertainty is true.",
    "Preserve positive and negative evidence. Never read credentials or environment secrets. Never perform Git mutations.",
    ...evidenceInstructions,
    ...(task.mode === "WRITE"
      ? ["The host reruns commands_tests after the final mutation and verifies write_verifications against raw bytes; never fabricate test results."]
      : []),
    "Complete the task by calling finish_handoff exactly once with all required fields.",
  ].join("\n");
  const contract = {
    contract_version: 5,
    status_vocabulary: ["PASS", "FAIL", "BLOCKED"],
    execution_status_vocabulary: [
      "ACCEPTED", "INCOMPLETE", "BLOCKED", "PROVIDER_ERROR", "CONTRACT_ERROR", "CANCELLED",
    ],
    evidence_verdict_vocabulary: [
      "POSITIVE", "NEGATIVE", "NULL", "MIXED", "UNRESOLVED", "NOT_APPLICABLE",
    ],
    final_json_keys: HANDOFF_KEYS,
    authority_boundary:
      "Sol retains architecture, science, policy, hypothesis interpretation, and final approval.",
    mode: task.mode,
    fast_only: task.fastOnly === true,
    model_tier: task.tier,
    allowed_paths: task.allowedPaths,
    required_reads: task.requiredReads,
    coverage_spec: task.coverageSpec
      ? {
          mode: task.coverageSpec.mode,
          citations_required_for: task.coverageSpec.citationsRequiredFor,
        }
      : null,
    forbidden_actions: task.forbiddenActions,
    commands_tests: task.commandsTests,
    write_verifications: task.writeVerifications ?? [],
    frozen_artifacts: frozenArtifactDescriptors(task.frozenArtifacts),
    frozen_artifact_payload_identity:
      task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
    definition_of_done: task.definitionOfDone,
    required_output: task.requiredOutput,
    route_constraints: task.routeConstraints,
    route_normalization: task.routeNormalization ?? null,
    provider_call_protocol: {
      maximum_calls: task.routeConstraints.maximumProviderCalls,
      final_call_reserved_for_handoff: task.packedEvidenceMode === null,
      packed_one_shot: task.packedEvidenceMode !== null,
    },
    execution_rule:
      task.mode === "READ_ONLY"
        ? "Do not edit, create, move, or delete files."
        : "Change only allowed_paths through the supplied write tools.",
    objective: task.objective,
    task_id: task.contractHash
      ? `CONTRACT-${task.contractHash}`
      : (task.jobId ?? "UNASSIGNED"),
  };
  const user = `TASK CONTRACT JSON\n${JSON.stringify(contract, null, 2)}`;
  if (system.length + user.length > MAX_PROMPT_CHARS) throw new Error("worker prompt is too large");
  return { system, user };
}

function buildLunaWorkerPrompt(task) {
  const base = buildWorkerPrompt(task);
  const system = base.system
    .replace(
      "You are a bounded DeepSeek repository worker invoked directly by Codex.",
      "You are a bounded GPT-5.6 Luna repository worker invoked by the Codex CLI.",
    )
    .replace(
      "Batch independent reads in one turn, never repeat equivalent tool arguments, and reserve the final provider turn for finish_handoff.",
      "Batch independent reads in one turn and never repeat equivalent tool arguments.",
    )
    .replace(
      "Complete the task by calling finish_handoff exactly once with all required fields.",
      "Return exactly one final JSON object containing every final_json_keys field; the Codex CLI validates it against the supplied output schema.",
    );
  return [
    system,
    "Work only inside the staged workspace supplied to Codex.",
    "Do not read credentials, environment secrets, or files outside that staged workspace.",
    "Do not use network access, nested agents, MCP servers, or Git mutations.",
    base.user,
  ].join("\n\n");
}

export function buildSolHeadPrompt(plan) {
  assertSolHeadPlan(plan);
  const contract = {
    contract_version: 1,
    plan_id: plan.plan_id,
    requested_model: SOL_HEAD.model,
    requested_effort: plan.route.selected_effort,
    allowed_actions: HEAD_ACTIONS,
    authority_domains: plan.route.authority_domains,
    route_contract: plan.route_contract,
    policy_hash: plan.policy_hash,
    evidence_hash: plan.evidence_hash,
    governance_hash: plan.governance_hash,
    allowed_paths: plan.task.allowedPaths,
    governance_paths: plan.governance_paths,
    objective: plan.task.objective,
    forbidden_actions: plan.task.forbiddenActions,
    commands_tests: plan.task.commandsTests,
    definition_of_done: plan.task.definitionOfDone,
    required_output: plan.task.requiredOutput,
    final_json_keys: HEAD_HANDOFF_KEYS,
  };
  const instructions = [
    "You are an isolated GPT-5.6 Sol head reviewer launched by an xhigh root engineer.",
    "This is read-only analysis. Do not write, create, move, rename, or delete files.",
    "Do not spawn nested agents or delegate directly; DELEGATE_BOUNDED only returns contracts to the outer xhigh scheduler.",
    "Do not call MCP servers or use network access. Do not perform Git mutations.",
    "Do not read, request, reveal, or persist credentials, secrets, tokens, or environment variables.",
    "Do not claim an in-place switch of the active root turn; this is a separate isolated job.",
    "Xhigh retains implementation and final approval for every architectural or scientific decision.",
    `Return exactly one action from: ${HEAD_ACTIONS.join(", ")}.`,
    "Use only staged evidence paths. Preserve positive and negative evidence and state uncertainty explicitly.",
    "Return exactly one final JSON object containing every final_json_keys field; the Codex CLI validates the output schema.",
  ].join("\n");
  const prompt = `${instructions}\n\nHEAD CONTRACT JSON\n${JSON.stringify(contract, null, 2)}`;
  if (prompt.length > MAX_PROMPT_CHARS) throw new Error("Sol head prompt is too large");
  return prompt;
}

export function buildDeepSeekRequest(
  task,
  messages,
  tools,
  { forceFinal = false, packedEvidence = null } = {},
) {
  const body = {
    model: task.model,
    messages,
    stream: false,
    max_tokens: task.maxOutputTokens,
  };
  if (task.requestDialect === "deepinfra-openai") {
    body.service_tier = task.serviceTier;
    body.reasoning_effort = task.reasoningEffort;
    if (task.tier === "PRO" || task.tier === "REASONING") {
      body.thinking = { type: "enabled" };
    } else {
      body.thinking = { type: "disabled" };
    }
  } else {
    body.user_id = `codex-${sha256(task.workspace).slice(0, 20)}`;
    body.thinking = {
      type: task.tier === "PRO" || task.tier === "REASONING" ? "enabled" : "disabled",
    };
    if (task.tier === "PRO" || task.tier === "REASONING") {
      body.reasoning_effort = task.reasoningEffort;
    }
  }
  if (tools.length > 0) {
    body.tools = tools;
    const thinkingEnabled =
      task.tier === "PRO" || task.tier === "REASONING";
    if (!thinkingEnabled) {
      body.tool_choice = forceFinal ? "none" : "auto";
    }
  }
  if (forceFinal) {
    if (
      task.requestDialect === "deepinfra-openai" &&
      new Set([
        FLASH_PACKED_EVIDENCE_MODE,
        FLASH_PACKED_WRITE_MODE,
      ]).has(task.packedEvidenceMode)
    ) {
      body.response_format = {
        type: "json_schema",
        json_schema: {
          name: task.packedEvidenceMode === FLASH_PACKED_WRITE_MODE
            ? "deepluna_flash_write_v2"
            : "deepluna_flash_handoff_v6",
          strict: true,
          schema: task.packedEvidenceMode === FLASH_PACKED_WRITE_MODE
            ? flashPackedWriteSchema(task, packedEvidence)
            : flashPackedHandoffSchema(packedEvidence),
        },
      };
      body.temperature = 0;
    } else {
      body.response_format = { type: "json_object" };
    }
  }
  return body;
}

async function hashFile(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(await readFile(filePath));
  return hash.digest("hex");
}

async function fingerprintPath(root, relativePath, state) {
  const fullPath = path.resolve(root, relativePath);
  if (!existsSync(fullPath)) return [`${relativePath}\0MISSING`];
  const realRoot = realpathSync(root);
  const realTarget = realpathSync(fullPath);
  if (!isWithin(realRoot, realTarget)) return [`${relativePath}\0OUTSIDE_SYMLINK`];
  const stat = statSync(realTarget);
  if (stat.isFile()) {
    state.files += 1;
    state.bytes += stat.size;
    if (state.files > MAX_CACHE_FILES || state.bytes > MAX_CACHE_BYTES) {
      throw new Error("cache fingerprint scope is too large");
    }
    return [`${portablePath(relativePath)}\0${stat.size}\0${await hashFile(realTarget)}`];
  }
  if (!stat.isDirectory()) return [`${relativePath}\0OTHER`];
  const records = [];
  const entries = readdirSync(realTarget, { withFileTypes: true }).sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  for (const entry of entries) {
    if (IGNORED_DIRECTORIES.has(entry.name)) continue;
    records.push(...(await fingerprintPath(root, path.join(relativePath, entry.name), state)));
  }
  return records;
}

export async function fingerprintAllowedPaths(workspace, allowedPaths) {
  const state = { files: 0, bytes: 0 };
  const records = [];
  for (const allowedPath of [...allowedPaths].sort()) {
    records.push(...(await fingerprintPath(workspace, allowedPath, state)));
  }
  return sha256(records.join("\n"));
}

function contractRecord(task) {
  return Object.freeze({
    contract_version: PROTOCOLS.contract,
    project_id: task.projectId ?? null,
    objective: task.objective,
    mode: task.mode,
    fast_only: task.fastOnly === true,
    tier: task.tier,
    model: task.model,
    primary_profile: task.primaryProfile,
    service_tier: task.serviceTier,
    reasoning_effort: task.reasoningEffort,
    allowed_paths: task.allowedPaths,
    required_reads: task.requiredReads ?? [],
    coverage_spec: task.coverageSpec ?? null,
    ...(task.packedEvidenceMode
      ? { packed_evidence_mode: task.packedEvidenceMode }
      : {}),
    ...(new Set([
      FLASH_PACKED_EVIDENCE_MODE,
      FLASH_PACKED_WRITE_MODE,
    ]).has(task.packedEvidenceMode)
      ? { packed_prompt_schema_version: FLASH_PACKED_PROMPT_SCHEMA_VERSION }
      : {}),
    forbidden_actions: task.forbiddenActions,
    commands_tests: task.commandsTests,
    local_assertions: task.localAssertions ?? [],
    write_verifications: task.writeVerifications ?? [],
    frozen_artifact_policy_version: task.frozenArtifactPolicyVersion ?? null,
    frozen_artifacts: frozenArtifactDescriptors(task.frozenArtifacts),
    frozen_artifact_payload_identity:
      task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
    ...(task.localCommandPolicyVersion
      ? {
          local_command_policy_version: task.localCommandPolicyVersion,
          local_runtime_identity: task.localRuntimeIdentity,
          local_command_specs: task.localCommandSpecs,
          local_dependency_identity: task.localDependencyIdentity ?? [],
        }
      : {}),
    ...(task.localExactWritePolicyVersion
      ? {
          local_exact_write_policy_version: task.localExactWritePolicyVersion,
          local_runtime_identity: task.localRuntimeIdentity,
        }
      : {}),
    definition_of_done: task.definitionOfDone,
    required_output: task.requiredOutput,
    max_output_tokens: task.maxOutputTokens,
    route_constraints: task.routeConstraints ?? null,
    route_normalization: task.routeNormalization ?? null,
  });
}

function durableTaskAuditRecord(task) {
  return Object.freeze({
    ...task,
    frozenArtifacts: frozenArtifactDescriptors(task.frozenArtifacts),
    frozenArtifactPayloadIdentity:
      task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
  });
}

export function buildContractHash(task) {
  return canonicalHash(contractRecord(task));
}

export function buildTaskFingerprint(task, scope = {}) {
  return sha256(
    stableJson({
      failureScopeVersion: 1,
      originThreadHash: scope.originThreadHash ?? null,
      workspaceInstanceId: task.workspaceInstanceId ?? scope.workspaceInstanceId ?? null,
      objective: task.objective,
      mode: task.mode,
      fastOnly: task.fastOnly === true,
      tier: task.tier,
      workspace: (task.requiredReads ?? []).length > 0 ? null : task.workspace,
      allowedPaths: task.allowedPaths,
      forbiddenActions: task.forbiddenActions,
      commandsTests: task.commandsTests,
      localAssertions: task.localAssertions ?? [],
      writeVerifications: task.writeVerifications ?? [],
      frozenArtifactPolicyVersion: task.frozenArtifactPolicyVersion ?? null,
      frozenArtifacts: frozenArtifactDescriptors(task.frozenArtifacts),
      frozenArtifactPayloadIdentity:
        task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
      localCommandPolicyVersion: task.localCommandPolicyVersion ?? null,
      localExactWritePolicyVersion: task.localExactWritePolicyVersion ?? null,
      localRuntimeIdentity: task.localRuntimeIdentity ?? null,
      localCommandSpecs: task.localCommandSpecs ?? [],
      localDependencyIdentity: task.localDependencyIdentity ?? [],
      definitionOfDone: task.definitionOfDone,
      requiredOutput: task.requiredOutput,
      maxOutputTokens: task.maxOutputTokens,
      primaryProfile: task.primaryProfile,
      model: task.model,
      serviceTier: task.serviceTier,
      reasoningEffort: task.reasoningEffort,
      projectId: task.projectId ?? null,
      routeConstraints: task.routeConstraints ?? null,
      contractHash: task.contractHash ?? null,
      inputManifestHash: task.inputManifestHash ?? null,
      coverageHash: task.coverageHash ?? canonicalHash(null),
      requiredReads: task.requiredReads ?? [],
      coverageSpec: task.coverageSpec ?? null,
      protocols: PROTOCOLS,
    }),
  );
}

export function buildCacheKey(
  task,
  fingerprint,
  protocols = PROTOCOLS,
  policyIdentity = CACHE_POLICY_IDENTITY,
) {
  return sha256(
    stableJson({
      protocols,
      policyIdentity,
      projectId: task.projectId ?? null,
      providerChain: [
        `${task.primaryRoute}:${task.model}:${task.serviceTier ?? "standard"}:${task.reasoningEffort}`,
        ...(task.fastOnly
          ? []
          : [`${LUNA_FALLBACK.provider}:${LUNA_FALLBACK.model}:${LUNA_FALLBACK.reasoning}`]),
        ...(task.routeConstraints?.allowedRoutes?.includes("GLM")
          ? [`${GLM_FALLBACK.provider}:${GLM_FALLBACK.model}:${GLM_FALLBACK.reasoning}:${GLM_FALLBACK.policy}`]
          : []),
      ],
      routeConstraints: task.routeConstraints ?? { fallbackPolicy: task.fallbackPolicy },
      contractHash: task.contractHash ?? null,
      inputManifestHash: task.inputManifestHash ?? null,
      coverageHash: task.coverageHash ?? canonicalHash(null),
      requiredReads: task.requiredReads ?? [],
      coverageSpec: task.coverageSpec ?? null,
      workspace: (task.requiredReads ?? []).length > 0 ? null : task.workspace,
      objective: task.objective,
      mode: task.mode,
      fastOnly: task.fastOnly === true,
      tier: task.tier,
      allowedPaths: task.allowedPaths,
      forbiddenActions: task.forbiddenActions,
      commandsTests: task.commandsTests,
      localAssertions: task.localAssertions ?? [],
      writeVerifications: task.writeVerifications ?? [],
      frozenArtifactPolicyVersion: task.frozenArtifactPolicyVersion ?? null,
      frozenArtifacts: frozenArtifactDescriptors(task.frozenArtifacts),
      frozenArtifactPayloadIdentity:
        task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
      localCommandPolicyVersion: task.localCommandPolicyVersion ?? null,
      localExactWritePolicyVersion: task.localExactWritePolicyVersion ?? null,
      localRuntimeIdentity: task.localRuntimeIdentity ?? null,
      localCommandSpecs: task.localCommandSpecs ?? [],
      localDependencyIdentity: task.localDependencyIdentity ?? [],
      definitionOfDone: task.definitionOfDone,
      requiredOutput: task.requiredOutput,
      maxOutputTokens: task.maxOutputTokens,
      fingerprint,
    }),
  );
}

function processAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function removeStaleLocks(lockRoot) {
  if (!existsSync(lockRoot)) return;
  const lockPattern = /^(writer|gate|provider-gate|reader-\d+|provider-(?:deepseek|luna|glm)-\d+)\.lock$/;
  for (const name of readdirSync(lockRoot)) {
    if (!lockPattern.test(name)) continue;
    const lockPath = path.join(lockRoot, name);
    try {
      if (!processAlive(Number(readJson(lockPath).pid))) unlinkSync(lockPath);
    } catch {
      try {
        unlinkSync(lockPath);
      } catch (error) {
        if (error?.code !== "ENOENT") throw error;
      }
    }
  }
}

function createLock(lockPath) {
  const descriptor = openSync(lockPath, "wx");
  try {
    writeFileSync(
      descriptor,
      JSON.stringify({ pid: process.pid, created_at: new Date().toISOString() }),
      "utf8",
    );
  } finally {
    closeSync(descriptor);
  }
}

function waitForLock(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function acquireStateLock(lockPath) {
  mkdirSync(path.dirname(lockPath), { recursive: true });
  const token = crypto.randomUUID();
  for (let attempt = 0; attempt < 200; attempt += 1) {
    try {
      const descriptor = openSync(lockPath, "wx");
      try {
        writeFileSync(
          descriptor,
          JSON.stringify({ pid: process.pid, token, created_at: new Date().toISOString() }),
          "utf8",
        );
      } finally {
        closeSync(descriptor);
      }
      let released = false;
      return () => {
        if (released) return;
        released = true;
        try {
          const current = readJson(lockPath);
          if (current.pid === process.pid && current.token === token) unlinkSync(lockPath);
        } catch {
          // A missing or replaced transaction lock is outside this owner's control.
        }
      };
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      let owner = null;
      try {
        owner = readJson(lockPath);
      } catch {
        // Malformed locks cannot prove a live owner and are safe to remove.
      }
      if (!owner || !processAlive(Number(owner.pid))) {
        try {
          unlinkSync(lockPath);
        } catch (unlinkError) {
          if (unlinkError?.code !== "ENOENT") throw unlinkError;
        }
        continue;
      }
      waitForLock(5);
    }
  }
  throw new Error(`timed out waiting for state transaction lock: ${lockPath}`);
}

export function acquireTaskLock(lockRoot, cacheKey, id) {
  mkdirSync(lockRoot, { recursive: true });
  const lockPath = path.join(lockRoot, `task-${cacheKey}.lock`);
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const descriptor = openSync(lockPath, "wx");
      try {
        writeFileSync(
          descriptor,
          JSON.stringify({
            pid: process.pid,
            job_id: id,
            cache_key: cacheKey,
            created_at: new Date().toISOString(),
          }),
          "utf8",
        );
      } finally {
        closeSync(descriptor);
      }
      let released = false;
      return {
        acquired: true,
        release() {
          if (released) return;
          released = true;
          try {
            const current = readJson(lockPath);
            if (current.job_id === id && current.pid === process.pid) unlinkSync(lockPath);
          } catch {
            // A missing or replaced lock is already outside this owner's control.
          }
        },
      };
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      let existing = null;
      try {
        existing = readJson(lockPath);
      } catch {
        // Malformed locks are stale and safe to replace.
      }
      if (existing?.job_id && processAlive(Number(existing.pid))) {
        return { acquired: false, job_id: existing.job_id, owner_pid: existing.pid };
      }
      try {
        unlinkSync(lockPath);
      } catch (unlinkError) {
        if (unlinkError?.code !== "ENOENT") throw unlinkError;
      }
    }
  }
  throw new Error("could not acquire exact-task single-flight lock");
}

export function acquireSlot(lockRoot, mode, preferredReader = null, maxReaderSlots = 2) {
  mkdirSync(lockRoot, { recursive: true });
  removeStaleLocks(lockRoot);
  const gatePath = path.join(lockRoot, "gate.lock");
  try {
    createLock(gatePath);
  } catch (error) {
    if (error?.code === "EEXIST") throw new Error("concurrency gate is busy");
    throw error;
  }
  let slotPath;
  try {
    const writerPath = path.join(lockRoot, "writer.lock");
    const safeMaxReaderSlots = Number.isInteger(maxReaderSlots) && maxReaderSlots > 0
      ? maxReaderSlots
      : 2;
    const readerPaths = Array.from({ length: safeMaxReaderSlots }, (_, index) => (
      path.join(lockRoot, `reader-${index}.lock`)
    ));
    if (mode === "WRITE") {
      if (existsSync(writerPath)) throw new Error("writer is active");
      if (readerPaths.some((item) => existsSync(item))) throw new Error("active readers block WRITE");
      slotPath = writerPath;
    } else {
      if (existsSync(writerPath)) throw new Error("writer is active");
      if (preferredReader) {
        slotPath = readerPaths[preferredReader.index];
        if (!slotPath) throw new Error("unknown reader lane");
        if (existsSync(slotPath)) {
          throw new Error(`${preferredReader.label} reader lane is busy`);
        }
      } else {
        slotPath = readerPaths.find((item) => !existsSync(item));
        if (!slotPath) throw new Error("all reader slots are busy");
      }
    }
    createLock(slotPath);
  } finally {
    if (existsSync(gatePath)) unlinkSync(gatePath);
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (slotPath && existsSync(slotPath)) unlinkSync(slotPath);
  };
}

function isDynamicPoolCapacityError(error) {
  return /(?:concurrency gate is busy|reader lane is busy|all reader slots are busy|writer is active|active readers block WRITE)/i.test(
    String(error?.message ?? ""),
  );
}

const FAST_READER_POOL_MODES = Object.freeze([
  "DYNAMIC",
  "DEDICATED",
  "FIXED_FIVE_SWARM",
]);

export function resolveFastReaderPoolPolicy({
  fastOnly = process.env.DEEPLUNA_FAST_ONLY === "1",
  mode = process.env.DEEPLUNA_READER_POOL_MODE,
  readLimit = process.env.NANODRUG_DEEPINFRA_READER_LANES,
  ownerProjectId = process.env.DEEPLUNA_READER_POOL_OWNER_PROJECT_ID,
  policyHash = null,
} = {}) {
  if (typeof fastOnly !== "boolean") {
    throw new TypeError("Fast reader pool fastOnly must be boolean");
  }
  const exactMode = String(mode ?? "DYNAMIC").trim().toUpperCase();
  if (!FAST_READER_POOL_MODES.includes(exactMode)) {
    throw new TypeError("Fast reader pool mode is invalid");
  }
  const exactReadLimit =
    readLimit === undefined || readLimit === null || String(readLimit).trim() === ""
      ? fastOnly ? 5 : 2
      : Number(String(readLimit).trim());
  if (!Number.isSafeInteger(exactReadLimit) || exactReadLimit < 1 || exactReadLimit > 8) {
    throw new TypeError("Fast reader pool limit must be between 1 and 8");
  }
  if (fastOnly && exactReadLimit !== 5) {
    throw new TypeError("Fast-only reader limit must be exactly 5");
  }
  if (!fastOnly && exactMode !== "DYNAMIC") {
    throw new TypeError("dedicated and fixed reader modes require Fast-only routing");
  }
  const rawOwner = ownerProjectId === undefined || ownerProjectId === null
    ? ""
    : String(ownerProjectId).trim();
  if (exactMode === "DYNAMIC" && rawOwner !== "") {
    throw new TypeError("dynamic Fast reader pool cannot have an owner project");
  }
  if (
    exactMode !== "DYNAMIC" &&
    !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(rawOwner)
  ) {
    throw new TypeError("owned Fast reader pool requires a valid project identity");
  }
  const core = Object.freeze({
    schemaVersion: 1,
    fastOnly,
    mode: exactMode,
    readLimit: exactReadLimit,
    writeLimit: 1,
    logicalLimit: 5,
    ownerProjectId: exactMode === "DYNAMIC" ? null : rawOwner,
  });
  const exactPolicyHash = sha256(stableJson(core));
  if (policyHash !== null && policyHash !== exactPolicyHash) {
    throw new TypeError("Fast reader pool policy hash is invalid");
  }
  return Object.freeze({
    ...core,
    policyHash: exactPolicyHash,
  });
}

function assertReaderPoolProject(policy, projectId) {
  if (policy.mode === "DYNAMIC" || policy.ownerProjectId === projectId) return;
  if (policy.mode === "DEDICATED") {
    throw new Error("dedicated Fast reader pool is owned by another project");
  }
  throw new Error("fixed five-worker swarm is owned by another project");
}

function acquireActiveReaderPoolPolicyLease(poolRoot, policy) {
  const policyRoot = path.join(poolRoot, "active-policy");
  mkdirSync(policyRoot, { recursive: true });
  const releaseGate = acquireStateLock(path.join(policyRoot, "gate.lock"));
  const token = crypto.randomUUID().replaceAll("-", "");
  const lockName = `policy-${policy.policyHash}-${process.pid}-${token}.lock`;
  const lockPath = path.join(policyRoot, lockName);
  try {
    for (const name of readdirSync(policyRoot)) {
      const match = /^policy-([a-f0-9]{64})-\d+-[a-f0-9]+\.lock$/.exec(name);
      if (match === null) continue;
      const candidatePath = path.join(policyRoot, name);
      let owner;
      try {
        owner = readJson(candidatePath);
      } catch {
        unlinkSync(candidatePath);
        continue;
      }
      if (!processAlive(Number(owner.pid))) {
        unlinkSync(candidatePath);
        continue;
      }
      if (match[1] !== policy.policyHash) {
        throw new Error("active Fast reader pool policy does not match this daemon");
      }
    }
    const descriptor = openSync(lockPath, "wx");
    try {
      writeFileSync(
        descriptor,
        JSON.stringify({
          pid: process.pid,
          token,
          policy_hash: policy.policyHash,
          created_at: new Date().toISOString(),
        }),
        "utf8",
      );
    } finally {
      closeSync(descriptor);
    }
  } finally {
    releaseGate();
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    try {
      const current = readJson(lockPath);
      if (current.pid === process.pid && current.token === token) unlinkSync(lockPath);
    } catch {
      // A missing or replaced policy lease is already outside this owner's control.
    }
  };
}

async function acquireDynamicPoolSlot(
  lockRoot,
  mode,
  maximumReaders,
  signal,
  pollDelayMs,
) {
  while (true) {
    if (signal?.aborted) {
      const error = new Error("dynamic pool admission was cancelled");
      error.code = "CANDIDATE_ATTEMPT_CANCELLED";
      throw error;
    }
    try {
      return acquireSlot(lockRoot, mode, null, maximumReaders);
    } catch (error) {
      if (!isDynamicPoolCapacityError(error)) throw error;
      await asyncDelay(pollDelayMs);
    }
  }
}

export async function acquireDynamicPoolLease({
  storeRoot = defaultStoreRoot(),
  projectId,
  taskId,
  mode,
  signal = null,
  pollDelayMs = 10,
  readerPoolPolicy = null,
} = {}) {
  const exactProjectId = resolveProjectId(projectId);
  const exactReaderPoolPolicy = resolveFastReaderPoolPolicy(
    readerPoolPolicy === null ? {} : readerPoolPolicy,
  );
  assertReaderPoolProject(exactReaderPoolPolicy, exactProjectId);
  const exactTaskId = String(taskId ?? "").trim();
  if (!/^[A-Za-z0-9._:-]{1,256}$/.test(exactTaskId)) {
    throw new TypeError("dynamic pool task identity is invalid");
  }
  if (!["READ_ONLY", "WRITE"].includes(mode)) {
    throw new TypeError("dynamic pool mode must be READ_ONLY or WRITE");
  }
  if (
    signal !== null &&
    (typeof signal !== "object" || typeof signal.aborted !== "boolean")
  ) {
    throw new TypeError("dynamic pool signal is invalid");
  }
  if (!Number.isSafeInteger(pollDelayMs) || pollDelayMs < 1 || pollDelayMs > 1_000) {
    throw new TypeError("dynamic pool poll delay is invalid");
  }
  const poolRoot = path.join(path.resolve(storeRoot), "dynamic-pool-v1");
  const logicalRoot = path.join(poolRoot, "logical");
  const physicalRoot = path.join(poolRoot, "physical");
  const releasePolicy = acquireActiveReaderPoolPolicyLease(
    poolRoot,
    exactReaderPoolPolicy,
  );
  let releaseLogical;
  let releasePhysical;
  try {
    releaseLogical = await acquireDynamicPoolSlot(
      logicalRoot,
      "READ_ONLY",
      exactReaderPoolPolicy.logicalLimit,
      signal,
      pollDelayMs,
    );
    releasePhysical = await acquireDynamicPoolSlot(
      physicalRoot,
      mode,
      exactReaderPoolPolicy.readLimit,
      signal,
      pollDelayMs,
    );
  } catch (error) {
    releaseLogical?.();
    releasePolicy();
    throw error;
  }
  let released = false;
  const release = () => {
    if (released) return;
    released = true;
    releasePhysical();
    releaseLogical();
    releasePolicy();
  };
  Object.defineProperties(release, {
    projectId: { value: exactProjectId, enumerable: true },
    taskId: { value: exactTaskId, enumerable: true },
    readerPoolMode: { value: exactReaderPoolPolicy.mode, enumerable: true },
    readerPoolPolicyHash: {
      value: exactReaderPoolPolicy.policyHash,
      enumerable: true,
    },
  });
  return Object.freeze(release);
}

const PRODUCTION_PUBLIC_WINDOWS_PATH =
  /(?:[A-Za-z]:[\\/]|\\\\)[^\s,;:)}\]]+/gu;
const PRODUCTION_PUBLIC_POSIX_PATH =
  /(^|\s)\/[A-Za-z0-9._-]+\/[^\s,;:)}\]]+/gu;

function boundedProductionPublicText(value, maximumBytes) {
  const text = String(value ?? "");
  if (Buffer.byteLength(text, "utf8") <= maximumBytes) return text;
  const suffix = " <TRUNCATED>";
  const byteLimit = maximumBytes - Buffer.byteLength(suffix, "utf8");
  const characters = [];
  let bytes = 0;
  for (const character of text) {
    const characterBytes = Buffer.byteLength(character, "utf8");
    if (bytes + characterBytes > byteLimit) break;
    characters.push(character);
    bytes += characterBytes;
  }
  return `${characters.join("")}${suffix}`;
}

function productionWorkerPublicText(value, fallback, maximumBytes) {
  const source =
    typeof value === "string" && value.trim().length > 0 ? value : fallback;
  const pathRedacted = source
    .replace(PRODUCTION_PUBLIC_WINDOWS_PATH, "[ABSOLUTE_PATH]")
    .replace(PRODUCTION_PUBLIC_POSIX_PATH, "$1[ABSOLUTE_PATH]");
  const diagnosticRedacted = redactDiagnostic(pathRedacted);
  const safe = containsUnsafePublicText(diagnosticRedacted)
    ? fallback
    : diagnosticRedacted;
  return boundedProductionPublicText(safe, maximumBytes);
}

function productionWorkerHandoff(result) {
  const status = ["PASS", "CACHED", "FAIL", "BLOCKED"].includes(result?.status)
    ? result.status
    : "FAIL";
  const accepted = status === "PASS" || status === "CACHED";
  const textArray = (value) => {
    if (!Array.isArray(value)) return [];
    return value.map((entry) => {
      let text;
      if (typeof entry === "string") {
        text = entry;
      } else if (
        entry !== null &&
        typeof entry === "object" &&
        !Array.isArray(entry) &&
        typeof entry.text === "string"
      ) {
        text = entry.text;
      } else {
        throw new TypeError(
          "production worker public list item must be text or typed text",
        );
      }
      return productionWorkerPublicText(
        text,
        "A worker finding was redacted from the public packet.",
        2048,
      );
    });
  };
  return Object.freeze({
    status,
    execution_status:
      typeof result?.execution_status === "string"
        ? result.execution_status
        : accepted
          ? "ACCEPTED"
          : status === "BLOCKED"
            ? "BLOCKED"
            : "INCOMPLETE",
    evidence_verdict:
      typeof result?.evidence_verdict === "string"
        ? result.evidence_verdict
        : accepted
          ? "NOT_APPLICABLE"
          : "UNRESOLVED",
    cache_hit: status === "CACHED" || result?.cache_hit === true,
    summary: productionWorkerPublicText(
      result?.summary,
      "The bounded DeepLuna worker completed without a textual summary.",
      4096,
    ),
    positive_findings: textArray(result?.positive_findings),
    negative_findings: textArray(result?.negative_findings),
    residual_risks: textArray(result?.residual_risks),
    recommended_next_action: productionWorkerPublicText(
      result?.recommended_next_action,
      "Return the compact handoff to the authenticated owning task.",
      4096,
    ),
    scientific_uncertainty: result?.scientific_uncertainty === true,
    architecture_uncertainty: result?.architecture_uncertainty === true,
    scope_deviation: result?.scope_deviation === true,
  });
}

export function createProductionCandidateWorkerRunner({
  storeRoot = defaultStoreRoot(),
  projectId = process.env.DEEPLUNA_PROJECT_ID,
  managerFactory = (options) => new JobManager(options),
  acquirePoolLease = acquireDynamicPoolLease,
  readerPoolPolicy = resolveFastReaderPoolPolicy(),
  pollDelayMs = 50,
} = {}) {
  const exactStoreRoot = path.resolve(storeRoot);
  const exactProjectId = resolveProjectId(projectId);
  const exactReaderPoolPolicy = resolveFastReaderPoolPolicy(readerPoolPolicy);
  assertReaderPoolProject(exactReaderPoolPolicy, exactProjectId);
  if (typeof managerFactory !== "function" || typeof acquirePoolLease !== "function") {
    throw new TypeError("production candidate runner dependencies are invalid");
  }
  if (!Number.isSafeInteger(pollDelayMs) || pollDelayMs < 1 || pollDelayMs > 1_000) {
    throw new TypeError("production candidate runner poll delay is invalid");
  }
  return async function runProductionCandidateWorker({
    contract,
    budgetController,
    signal,
  } = {}) {
    if (
      contract === null ||
      typeof contract !== "object" ||
      contract.projectId !== exactProjectId ||
      !["READER", "WRITER"].includes(contract.role) ||
      contract.payload === null ||
      typeof contract.payload !== "object"
    ) {
      throw new TypeError("production candidate contract is invalid");
    }
    const mode = contract.payload.mode;
    if (
      !["READ_ONLY", "WRITE"].includes(mode) ||
      (mode === "WRITE") !== (contract.role === "WRITER")
    ) {
      throw new TypeError("production candidate role does not match its mode");
    }
    const originContext = contract.payload.originContext;
    if (
      originContext === null ||
      typeof originContext !== "object" ||
      !/^[a-f0-9]{64}$/.test(originContext.originThreadHash ?? "") ||
      !/^[a-f0-9]{64}$/.test(originContext.originCapabilityHash ?? "")
    ) {
      throw new TypeError("production candidate origin context is invalid");
    }
    if (
      budgetController?.isDurableTransmissionController !== true ||
      budgetController?.cumulativeBudgetSafe !== true
    ) {
      throw new Error("production candidate cumulative budget controller is unsafe");
    }
    const releasePool = await acquirePoolLease({
      storeRoot: exactStoreRoot,
      projectId: exactProjectId,
      taskId: contract.jobId,
      mode,
      signal,
      readerPoolPolicy: exactReaderPoolPolicy,
    });
    let manager = null;
    let submitted = null;
    try {
      manager = managerFactory({
        storeRoot: exactStoreRoot,
        projectId: exactProjectId,
        originContext: Object.freeze({ ...originContext }),
        budgetController,
        jobIdFactory: () => contract.jobId,
      });
      submitted = await manager.submit(contract.payload.input, mode);
      let result = submitted;
      let statusPolled = false;
      while (new Set(["QUEUED", "RUNNING"]).has(result.status)) {
        if (signal?.aborted) {
          await manager.cancel?.(submitted.job_id);
          const error = new Error("production candidate worker was cancelled");
          error.code = "CANDIDATE_ATTEMPT_CANCELLED";
          throw error;
        }
        await asyncDelay(pollDelayMs);
        result = await manager.status(submitted.job_id, { includeHandoff: true });
        statusPolled = true;
      }
      if (!statusPolled) {
        result = await manager.status(submitted.job_id, { includeHandoff: true });
      }
      return Object.freeze({
        result: Object.freeze({ handoff: productionWorkerHandoff(result) }),
        usage: Object.freeze({
          actualNanoUsd: 0,
          inputTokens: 0,
          outputTokens: 0,
        }),
      });
    } finally {
      releasePool();
    }
  };
}

export function acquireProviderSlot(lockRoot, mode, provider) {
  const providerPolicy = {
    deepseek: { capacity: 8, label: "Primary" },
    luna: { capacity: 1, label: "Luna" },
    glm: { capacity: 1, label: "GLM" },
  }[provider];
  if (!providerPolicy) throw new Error(`unknown provider lane: ${provider}`);

  mkdirSync(lockRoot, { recursive: true });
  removeStaleLocks(lockRoot);
  const releaseGate = acquireStateLock(path.join(lockRoot, "provider-gate.lock"));
  let slotPath;
  try {
    const writerPath = path.join(lockRoot, "writer.lock");
    const providerReaderPattern = /^provider-(deepseek|luna|glm)-\d+\.lock$/;
    const activeProviderReaders = readdirSync(lockRoot)
      .filter((name) => providerReaderPattern.test(name));
    const legacyReaders = readdirSync(lockRoot)
      .filter((name) => /^reader-\d+\.lock$/.test(name));
    if (mode === "WRITE") {
      if (existsSync(writerPath)) throw new Error("writer is active");
      if (activeProviderReaders.length > 0 || legacyReaders.length > 0) {
        throw new Error("active readers block WRITE");
      }
      slotPath = writerPath;
    } else {
      if (mode !== "READ_ONLY") throw new Error(`unknown provider mode: ${mode}`);
      if (existsSync(writerPath)) throw new Error("writer is active");
      const candidatePaths = Array.from(
        { length: providerPolicy.capacity },
        (_, index) => path.join(lockRoot, `provider-${provider}-${index}.lock`),
      );
      slotPath = candidatePaths.find((candidate) => !existsSync(candidate));
      if (!slotPath) {
        const capacityError = new Error(`${providerPolicy.label} reader capacity is busy`);
        capacityError.code = "PROVIDER_CAPACITY";
        throw capacityError;
      }
    }
    createLock(slotPath);
  } finally {
    releaseGate();
  }

  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (slotPath && existsSync(slotPath)) unlinkSync(slotPath);
  };
}

function isProviderCapacityError(error) {
  const message = String(error?.message ?? "");
  return error?.code === "PROVIDER_CAPACITY" || /PROVIDER_CAPACITY/i.test(message)
    || /Primary reader lane is busy/i.test(message)
    || /reader lane is busy/i.test(message);
}

function parseCandidate(candidate) {
  const trimmed = String(candidate ?? "").trim();
  const attempts = [trimmed];
  attempts.push(...[...trimmed.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi)].map((match) => match[1].trim()));
  for (const attempt of attempts) {
    try {
      const parsed = JSON.parse(attempt);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
    } catch {
      // Continue to the next candidate.
    }
  }
  return null;
}

export function truncateWords(value, maximum) {
  const words = String(value).trim().split(/\s+/).filter(Boolean);
  if (words.length <= maximum) return words.join(" ");
  return `${words.slice(0, maximum).join(" ")} ...`;
}

function resolveToolPath(task, value) {
  if (typeof value !== "string" || !value.trim() || path.isAbsolute(value)) {
    throw new Error(`path is not allowed: ${value}`);
  }
  const relative = portablePath(value.trim());
  if (CREDENTIAL_PATTERN.test(relative)) throw new Error(`credential path is forbidden: ${value}`);
  const fullPath = path.resolve(task.workspace, relative);
  if (!isWithin(task.workspace, fullPath)) throw new Error(`path is not allowed: ${value}`);
  const allowed = task.allowedPaths.some((item) => {
    const boundary = path.resolve(task.workspace, item);
    return isWithin(boundary, fullPath);
  });
  if (!allowed) throw new Error(`path is not allowed: ${value}`);

  let existing = fullPath;
  while (!existsSync(existing)) {
    const parent = path.dirname(existing);
    if (parent === existing) break;
    existing = parent;
  }
  if (existsSync(existing) && !isWithin(realpathSync(task.workspace), realpathSync(existing))) {
    throw new Error(`path resolves outside workspace: ${value}`);
  }
  if (existsSync(fullPath) && !isWithin(realpathSync(task.workspace), realpathSync(fullPath))) {
    throw new Error(`path resolves outside workspace: ${value}`);
  }
  return { relative, fullPath };
}

function resolveRequiredReadPath(task, value) {
  if (typeof value !== "string" || !value.trim() || path.isAbsolute(value)) {
    throw new Error(`required read path is not allowed: ${value}`);
  }
  const relative = portablePath(value.trim());
  if (CREDENTIAL_PATTERN.test(relative)) {
    throw new Error(`credential path is forbidden: ${value}`);
  }
  if (!task.requiredReads?.some((read) => read.path === relative)) {
    throw new Error(`path is not a declared required read: ${value}`);
  }
  const fullPath = path.resolve(task.workspace, relative);
  if (!isWithin(task.workspace, fullPath)) {
    throw new Error(`required read path is outside workspace: ${value}`);
  }
  if (
    !existsSync(fullPath) ||
    pathContainsReparsePoint(task.workspace, fullPath) ||
    !lstatSync(fullPath).isFile() ||
    (
      !relativePathIsAllowed(task, relative) &&
      lstatSync(fullPath).nlink !== 1
    ) ||
    !isWithin(realpathSync(task.workspace), realpathSync(fullPath))
  ) {
    throw new Error(`required evidence is not a regular workspace file: ${value}`);
  }
  return { relative, fullPath };
}

function resolveReadableToolPath(task, value) {
  try {
    return resolveToolPath(task, value);
  } catch (error) {
    if (
      task.mode === "WRITE" &&
      task.requiredReads?.some(
        (read) => read.path === portablePath(String(value ?? "").trim()),
      )
    ) {
      return resolveRequiredReadPath(task, value);
    }
    throw error;
  }
}

function boundedText(value, maximum = MAX_TOOL_RESULT_CHARS) {
  const text = String(value ?? "");
  return text.length <= maximum ? text : `${text.slice(0, maximum)}\n<TRUNCATED>`;
}

function enumerateFiles(task, relativePath) {
  const target = resolveToolPath(task, relativePath);
  if (!existsSync(target.fullPath)) throw new Error(`path does not exist: ${relativePath}`);
  const files = [];
  const visit = (fullPath) => {
    if (files.length >= MAX_LIST_FILES) return;
    const stat = statSync(fullPath);
    if (stat.isFile()) {
      files.push(portablePath(path.relative(task.workspace, fullPath)));
      return;
    }
    if (!stat.isDirectory()) return;
    for (const entry of readdirSync(fullPath, { withFileTypes: true }).sort((a, b) =>
      a.name.localeCompare(b.name),
    )) {
      if (IGNORED_DIRECTORIES.has(entry.name)) continue;
      const child = path.join(fullPath, entry.name);
      if (!isWithin(realpathSync(task.workspace), realpathSync(child))) continue;
      visit(child);
      if (files.length >= MAX_LIST_FILES) break;
    }
  };
  visit(target.fullPath);
  return files;
}

function readTextFile(filePath) {
  const stat = statSync(filePath);
  if (!stat.isFile()) throw new Error("path is not a file");
  if (stat.size > MAX_READ_FILE_BYTES) throw new Error("file exceeds bounded read size");
  const content = readFileSync(filePath, "utf8");
  if (content.includes("\0")) throw new Error("binary file reads are forbidden");
  return content;
}

function archiveExisting(task, relative, fullPath) {
  if (!existsSync(fullPath)) return null;
  const archiveRoot = path.join(task.workspace, ".archive");
  mkdirSync(archiveRoot, { recursive: true });
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const suffix = crypto.randomBytes(2).toString("hex");
  const archiveName = `${path.basename(relative)}.${stamp}_${suffix}.bak`;
  const archivePath = path.join(archiveRoot, archiveName);
  copyFileSync(fullPath, archivePath);
  return portablePath(path.relative(task.workspace, archivePath));
}

export async function runApprovedCommand(
  command,
  {
    cwd,
    timeoutMs = 300_000,
    signal,
    commandSpec = null,
    snapshotContent,
    capturedSha256,
    nodeModuleType,
  } = {},
) {
  if (commandSpec && !Buffer.isBuffer(snapshotContent)) {
    throw new Error("approved LOCAL command requires captured snapshot bytes");
  }
  if (commandSpec?.kind === "GET_CONTENT") {
    return {
      exit_code: 0,
      stdout: snapshotContent.toString("utf8"),
      stderr: "",
    };
  }
  if (commandSpec?.kind === "GET_FILE_HASH_SHA256") {
    const actualHash = sha256(snapshotContent);
    if (actualHash !== capturedSha256) {
      throw new Error("captured LOCAL command bytes changed before hashing");
    }
    return {
      exit_code: 0,
      stdout: `${actualHash.toUpperCase()}${os.EOL}`,
      stderr: "",
    };
  }
  return new Promise((resolve, reject) => {
    let executable;
    let args;
    if (commandSpec) {
      if (commandSpec.kind === "NODE_CHECK") {
        if (!new Set(["commonjs", "module"]).has(nodeModuleType)) {
          throw new Error("approved node --check requires a captured module context");
        }
        executable = process.execPath;
        args = ["--check", `--input-type=${nodeModuleType}`];
      } else {
        throw new Error("approved LOCAL command kind is unsupported");
      }
    } else {
      executable = process.platform === "win32" ? "powershell.exe" : "/bin/sh";
      args =
        process.platform === "win32"
          ? ["-NoProfile", "-NonInteractive", "-Command", command]
          : ["-lc", command];
    }
    const child = spawn(executable, args, { cwd, shell: false, windowsHide: true });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      signal?.removeEventListener("abort", onAbort);
      callback();
    };
    const onAbort = () => {
      child.kill();
      const error = new Error("command aborted");
      error.name = "AbortError";
      finish(() => reject(error));
    };
    const timeout = setTimeout(() => {
      child.kill();
      finish(() => resolve({ exit_code: 124, stdout, stderr: `${stderr}\ncommand timed out` }));
    }, timeoutMs);
    timeout.unref?.();
    if (signal?.aborted) return onAbort();
    signal?.addEventListener("abort", onAbort, { once: true });
    child.stdout.on("data", (chunk) => {
      stdout = boundedText(`${stdout}${chunk.toString("utf8")}`, MAX_COMMAND_OUTPUT_CHARS);
    });
    child.stderr.on("data", (chunk) => {
      stderr = boundedText(`${stderr}${chunk.toString("utf8")}`, MAX_COMMAND_OUTPUT_CHARS);
    });
    child.on("error", (error) => finish(() => reject(error)));
    child.on("close", (code) =>
      finish(() => resolve({ exit_code: code ?? 1, stdout, stderr })),
    );
    if (commandSpec?.kind === "NODE_CHECK") {
      child.stdin.end(snapshotContent);
    }
  });
}

function handoffToolSchema({ requireCitations = false } = {}) {
  const boundedList = (maxItems = 3, maxLength = 180) => ({
    type: "array",
    maxItems,
    items: { type: "string", maxLength },
  });
  const evidencePaths = () => boundedList(8, 200);
  return {
    type: "object",
    properties: {
      status: { type: "string", enum: ["PASS", "FAIL", "BLOCKED"] },
      execution_status: {
        type: "string",
        enum: ["ACCEPTED", "INCOMPLETE", "BLOCKED", "PROVIDER_ERROR", "CONTRACT_ERROR", "CANCELLED"],
      },
      evidence_verdict: {
        type: "string",
        enum: ["POSITIVE", "NEGATIVE", "NULL", "MIXED", "UNRESOLVED", "NOT_APPLICABLE"],
      },
      summary: { type: "string", maxLength: 600 },
      files_inspected: evidencePaths(),
      files_changed: evidencePaths(),
      commands_run: boundedList(),
      tests: boundedList(),
      positive_findings: boundedList(),
      negative_findings: boundedList(),
      citations: {
        type: "array",
        maxItems: 24,
        items: {
          type: "object",
          properties: {
            finding_field: {
              type: "string",
              enum: ["positive_findings", "negative_findings"],
            },
            finding_index: { type: "integer", minimum: 0 },
            evidence_id: { type: "string", pattern: "^EV-[a-f0-9]{32}$" },
            start: { type: "integer", minimum: 1 },
            end: { type: "integer", minimum: 1 },
            unit: { type: "string", enum: ["line"] },
          },
          required: [
            "finding_field",
            "finding_index",
            "evidence_id",
            "start",
            "end",
            "unit",
          ],
          additionalProperties: false,
        },
      },
      scientific_uncertainty: { type: "boolean" },
      architecture_uncertainty: { type: "boolean" },
      scope_deviation: { type: "boolean" },
      residual_risks: boundedList(),
      recommended_next_action: { type: "string", maxLength: 300 },
    },
    required: requireCitations ? [...HANDOFF_KEYS, "citations"] : [...HANDOFF_KEYS],
    additionalProperties: false,
  };
}

function flashPackedCitationSchema(pack) {
  if (
    !pack ||
    !Array.isArray(pack.sections) ||
    pack.sections.length < 1 ||
    pack.sections.length > MAX_GLM_PACKED_SECTIONS
  ) {
    throw new Error("Flash packed V6 schema requires 1 to 128 receipted sections");
  }
  const seenEvidenceIds = new Set();
  const branches = pack.sections.map((section, index) => {
    const label = `Flash packed V6 section[${index}]`;
    if (!/^EV-[a-f0-9]{32}$/.test(section?.evidence_id ?? "")) {
      throw new Error(`${label}.evidence_id is invalid`);
    }
    if (seenEvidenceIds.has(section.evidence_id)) {
      throw new Error("Flash packed V6 schema contains a duplicate evidence_id");
    }
    seenEvidenceIds.add(section.evidence_id);
    if (
      !Number.isSafeInteger(section.start) ||
      !Number.isSafeInteger(section.end) ||
      section.start < 1 ||
      section.end < section.start
    ) {
      throw new Error(`${label} has an invalid receipted range`);
    }
    return {
      type: "object",
      properties: {
        evidence_id: { type: "string", enum: [section.evidence_id] },
        start: {
          type: "integer",
          minimum: section.start,
          maximum: section.end,
        },
        end: {
          type: "integer",
          minimum: section.start,
          maximum: section.end,
        },
        unit: { type: "string", enum: ["line"] },
      },
      required: ["evidence_id", "start", "end", "unit"],
      additionalProperties: false,
    };
  });
  return { anyOf: branches };
}

function flashPackedHandoffSchema(pack) {
  const schema = handoffToolSchema();
  const citation = flashPackedCitationSchema(pack);
  const findings = {
    type: "array",
    maxItems: 3,
    items: {
      type: "object",
      properties: {
        text: { type: "string", minLength: 1, maxLength: 180 },
        citation,
      },
      required: ["text", "citation"],
      additionalProperties: false,
    },
  };
  delete schema.properties.citations;
  schema.properties.positive_findings = findings;
  schema.properties.negative_findings = findings;
  schema.required = [...HANDOFF_KEYS];
  return schema;
}

function flashPackedWriteSchema(task, pack) {
  const schema = flashPackedHandoffSchema(pack);
  const exactPaths = [...new Set(task.allowedPaths)];
  if (exactPaths.length < 1) {
    throw new Error("Flash packed WRITE schema requires exact allowed paths");
  }
  const frozenReferenceBranches = frozenArtifactDescriptors(task.frozenArtifacts).map(
    (artifact) => ({
      type: "object",
      properties: {
        kind: { type: "string", enum: ["write_frozen_file"] },
        path: { type: "string", enum: [artifact.path] },
        artifact_id: { type: "string", enum: [artifact.artifact_id] },
        sha256: { type: "string", enum: [artifact.sha256] },
        byte_length: {
          type: "integer",
          minimum: artifact.byte_length,
          maximum: artifact.byte_length,
        },
      },
      required: ["kind", "path", "artifact_id", "sha256", "byte_length"],
      additionalProperties: false,
    }),
  );
  schema.properties.write_operations = {
    type: "array",
    maxItems: 8,
    items: {
      anyOf: [
        {
          type: "object",
          properties: {
            kind: { type: "string", enum: ["replace_text"] },
            path: { type: "string", enum: exactPaths },
            old_text: { type: "string", minLength: 1, maxLength: MAX_WRITE_CHARS },
            new_text: { type: "string", maxLength: MAX_WRITE_CHARS },
          },
          required: ["kind", "path", "old_text", "new_text"],
          additionalProperties: false,
        },
        {
          type: "object",
          properties: {
            kind: { type: "string", enum: ["write_file"] },
            path: { type: "string", enum: exactPaths },
            content: { type: "string", maxLength: MAX_WRITE_CHARS },
          },
          required: ["kind", "path", "content"],
          additionalProperties: false,
        },
        ...frozenReferenceBranches,
      ],
    },
  };
  schema.required = [...schema.required, "write_operations"];
  return schema;
}

function headHandoffSchema() {
  const boundedList = (maxItems = 8, maxLength = 400) => ({
    type: "array",
    maxItems,
    items: { type: "string", maxLength },
  });
  return {
    type: "object",
    properties: {
      action: { type: "string", enum: [...HEAD_ACTIONS] },
      summary: { type: "string", maxLength: 800 },
      evidence_paths: boundedList(12, 240),
      decision: { type: "string", maxLength: 2_000 },
      requested_evidence: boundedList(),
      bounded_delegations: boundedList(),
      recommended_effort: { type: "string", enum: [...SOL_HEAD.efforts, "NONE"] },
      scientific_uncertainty: { type: "boolean" },
      architecture_uncertainty: { type: "boolean" },
      residual_risks: boundedList(),
      recommended_next_action: { type: "string", maxLength: 500 },
    },
    required: [...HEAD_HANDOFF_KEYS],
    additionalProperties: false,
  };
}

function assertSolHeadPlan(plan) {
  if (!plan || typeof plan !== "object" || Array.isArray(plan)) {
    throw new Error("Sol head plan must be an object");
  }
  if (!/^SRP-[a-f0-9]{32}$/.test(String(plan.plan_id ?? ""))) {
    throw new Error("invalid Sol head plan_id");
  }
  if (plan.provider !== SOL_HEAD.provider || plan.model !== SOL_HEAD.model) {
    throw new Error("Sol head plan provider identity does not match the runtime");
  }
  if (plan.route?.action !== "START_SOL_HEAD") {
    throw new Error(`Sol head plan is not launch eligible: ${plan.route?.action ?? "UNKNOWN"}`);
  }
  if (!SOL_HEAD.efforts.includes(plan.route?.selected_effort)) {
    throw new Error("Sol head plan has an invalid selected effort");
  }
  if (!plan.task || plan.task.mode !== "READ_ONLY") {
    throw new Error("Sol head plans must be READ_ONLY");
  }
  if (!Array.isArray(plan.task.allowedPaths) || !Array.isArray(plan.governance_paths)) {
    throw new Error("Sol head plan is missing bounded paths");
  }
  return plan;
}

function headExecutionTask(plan) {
  assertSolHeadPlan(plan);
  const workspace = realpathSync(path.resolve(plan.task.workspace));
  const allowedPaths = [...new Set([
    ...plan.task.allowedPaths,
    ...plan.governance_paths,
  ].map((relative) => normalizeAllowedPath(workspace, relative)))];
  return Object.freeze({
    ...plan.task,
    taskId: plan.plan_id,
    workspace,
    mode: "READ_ONLY",
    allowedPaths,
  });
}

function normalizeHeadHandoff(candidate, plan, executionTask) {
  if (!candidate || !HEAD_HANDOFF_KEYS.every((key) => Object.hasOwn(candidate, key))) {
    throw new Error("Sol head did not return the required structured handoff");
  }
  const action = String(candidate.action ?? "").toUpperCase();
  if (!HEAD_ACTIONS.includes(action)) throw new Error(`invalid Sol head action: ${action}`);
  const summary = String(candidate.summary ?? "").trim();
  if (!summary) throw new Error("Sol head summary must not be empty");
  const evidencePaths = [...new Set(safeArray(candidate.evidence_paths).map((relative) => {
    const normalized = normalizeAllowedPath(executionTask.workspace, relative);
    if (!relativePathIsAllowed(executionTask, normalized)) {
      throw new Error(`Sol head evidence path is outside the staged allowlist: ${relative}`);
    }
    return normalized;
  }))];
  const requestedEvidence = safeArray(candidate.requested_evidence);
  const boundedDelegations = safeArray(candidate.bounded_delegations);
  const recommendedEffort = String(candidate.recommended_effort ?? "").toLowerCase();
  if (![...SOL_HEAD.efforts, "none"].includes(recommendedEffort)) {
    throw new Error(`invalid recommended_effort: ${candidate.recommended_effort}`);
  }
  const decision = String(candidate.decision ?? "").trim();
  if (action === "RETURN_DECISION" && !decision) {
    throw new Error("RETURN_DECISION requires a decision");
  }
  if (action === "REQUEST_EVIDENCE" && requestedEvidence.length === 0) {
    throw new Error("REQUEST_EVIDENCE requires requested_evidence");
  }
  if (action === "DELEGATE_BOUNDED" && boundedDelegations.length === 0) {
    throw new Error("DELEGATE_BOUNDED requires bounded_delegations");
  }
  if (action === "DOWNGRADE" && !["medium", "high", "xhigh"].includes(recommendedEffort)) {
    throw new Error("DOWNGRADE requires medium, high, or xhigh");
  }
  return {
    action,
    summary,
    evidence_paths: evidencePaths,
    decision,
    requested_evidence: requestedEvidence,
    bounded_delegations: boundedDelegations,
    recommended_effort: recommendedEffort === "none" ? "NONE" : recommendedEffort,
    scientific_uncertainty: Boolean(candidate.scientific_uncertainty),
    architecture_uncertainty: Boolean(candidate.architecture_uncertainty),
    residual_risks: safeArray(candidate.residual_risks),
    recommended_next_action: String(candidate.recommended_next_action ?? "Return to xhigh."),
    plan_id: plan.plan_id,
  };
}

function safeDiagnosticText(value, knownSecrets = [], maximum = 2_000) {
  const candidate = value instanceof Error ? value.message : value;
  const redacted = redactDiagnostic(candidate ?? "", knownSecrets);
  const text = typeof redacted === "string" ? redacted : JSON.stringify(redacted);
  return boundedText(text, maximum);
}

function resolveCodexCandidatesViaPath(runner = spawnSync) {
  if (process.platform !== "win32") return [];
  try {
    const whereResult = runner("where.exe", ["codex"], {
      encoding: "utf8",
      windowsHide: true,
      maxBuffer: 64 * 1024,
    });
    if (whereResult?.error || Number(whereResult?.status ?? 0) !== 0) return [];
    return String(whereResult.stdout ?? "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

export function selectWindowsCodexLaunch(
  candidates,
  {
    fileExists = existsSync,
    nodeExecutable = process.execPath,
  } = {},
) {
  for (const candidate of Array.isArray(candidates) ? candidates : []) {
    const value = String(candidate ?? "").trim();
    if (!value) continue;
    const resolved = path.win32.normalize(value);
    if (path.win32.basename(resolved).toLowerCase() === "where.exe") continue;
    if (!fileExists(resolved)) continue;
    const extension = path.win32.extname(resolved).toLowerCase();
    if (extension === ".js") {
      return { executable: nodeExecutable, prefixArgs: [resolved] };
    }
    if (extension === ".exe" || extension === ".com") {
      return { executable: resolved, prefixArgs: [] };
    }
  }
  return null;
}

function resolveExplicitCodexLaunch({
  explicitLauncher = process.env.DEEPLUNA_CODEX_EXECUTABLE,
  platform = process.platform,
  fileExists = existsSync,
  nodeExecutable = process.execPath,
} = {}) {
  const raw = String(explicitLauncher ?? "").trim();
  if (!raw) return null;
  if (platform !== "win32") {
    if (!raw.includes("\\") && !raw.includes("/") && !raw.includes(":")) {
      return { executable: raw, prefixArgs: [] };
    }
    const resolved = path.resolve(raw);
    if (!fileExists(resolved)) {
      throw new Error(`Codex executable is unavailable: ${raw}`);
    }
    if (path.extname(resolved).toLowerCase() === ".js") {
      return { executable: nodeExecutable, prefixArgs: [resolved] };
    }
    return { executable: resolved, prefixArgs: [] };
  }

  const resolved = path.win32.resolve(raw);
  const launch = selectWindowsCodexLaunch([resolved], { fileExists, nodeExecutable });
  if (!launch) {
    throw new Error(
      "DEEPLUNA_CODEX_EXECUTABLE must resolve to an existing .exe, .com, or .js file on Windows",
    );
  }
  return launch;
}

export function defaultCodexLaunch({
  platform = process.platform,
  explicitLauncher = process.env.DEEPLUNA_CODEX_EXECUTABLE,
  pathFinder = resolveCodexCandidatesViaPath,
  appData = process.env.APPDATA ?? path.join(os.homedir(), "AppData", "Roaming"),
  fileExists = existsSync,
  nodeExecutable = process.execPath,
} = {}) {
  if (platform !== "win32") return { executable: "codex", prefixArgs: [] };

  const explicit = resolveExplicitCodexLaunch({
    explicitLauncher,
    platform,
    fileExists,
    nodeExecutable,
  });
  if (explicit) return explicit;

  const entrypoint = path.win32.join(
    appData,
    "npm",
    "node_modules",
    "@openai",
    "codex",
    "bin",
    "codex.js",
  );
  const installed = selectWindowsCodexLaunch([entrypoint], {
    fileExists,
    nodeExecutable,
  });
  if (installed) return installed;

  const discovered = selectWindowsCodexLaunch(pathFinder(), {
    fileExists,
    nodeExecutable,
  });
  if (discovered) return discovered;

  throw new Error(`Codex npm entrypoint is unavailable: ${entrypoint}`);
}

export function stageAllowedPaths(task, jobDirectory) {
  const stagedRoot = path.join(jobDirectory, "luna-workspace");
  rmSync(stagedRoot, { recursive: true, force: true });
  mkdirSync(stagedRoot, { recursive: true });
  for (const relative of task.allowedPaths) {
    const source = resolveToolPath(task, relative).fullPath;
    if (!existsSync(source)) throw new Error(`path does not exist: ${relative}`);
    if (pathContainsReparsePoint(task.workspace, source)) {
      throw new Error(`symbolic links and junctions are forbidden: ${relative}`);
    }
    if (lstatSync(source).isFile() && lstatSync(source).nlink !== 1) {
      throw new Error(`hard-linked WRITE targets are forbidden: ${relative}`);
    }
    const destination = path.join(stagedRoot, relative);
    mkdirSync(path.dirname(destination), { recursive: true });
    cpSync(source, destination, {
      recursive: true,
      dereference: false,
      errorOnExist: false,
      force: true,
      filter: (candidate) => {
        const candidateRelative = portablePath(path.relative(task.workspace, candidate));
        if (CREDENTIAL_PATTERN.test(candidateRelative)) return false;
        const parts = candidateRelative.split("/");
        if (parts.some((part) => IGNORED_DIRECTORIES.has(part))) return false;
        if (lstatSync(candidate).isSymbolicLink()) {
          throw new Error(`symbolic links are forbidden: ${candidateRelative}`);
        }
        return true;
      },
    });
  }
  return realpathSync(stagedRoot);
}

function collectTreeFiles(root, { skipIgnored = false } = {}) {
  if (!existsSync(root)) return [];
  if (lstatSync(root).isSymbolicLink()) throw new Error("symbolic links are forbidden");
  if (statSync(root).isFile()) return [root];
  const files = [];
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (skipIgnored && IGNORED_DIRECTORIES.has(entry.name)) continue;
      const fullPath = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error(`symbolic links are forbidden: ${fullPath}`);
      if (entry.isDirectory()) visit(fullPath);
      else if (entry.isFile()) files.push(fullPath);
    }
  };
  visit(root);
  return files;
}

function relativePathIsAllowed(task, relative) {
  const target = path.resolve(task.workspace, relative);
  return task.allowedPaths.some((allowedPath) =>
    isWithin(path.resolve(task.workspace, allowedPath), target),
  );
}

function frozenArtifactForPath(task, relative) {
  const identity = writeVerificationPathIdentity(relative);
  return (task.frozenArtifacts ?? []).find(
    (artifact) => writeVerificationPathIdentity(artifact.path) === identity,
  ) ?? null;
}

function collectStagedTextChanges(task, stagedRoot) {
  if (task.mode !== "WRITE") throw new Error("staged changes require WRITE mode");
  const originalFiles = new Set();
  for (const allowedPath of task.allowedPaths) {
    const target = resolveToolPath(task, allowedPath).fullPath;
    for (const filePath of collectTreeFiles(target, { skipIgnored: true })) {
      originalFiles.add(portablePath(path.relative(task.workspace, filePath)));
    }
  }

  const stagedFiles = new Map();
  for (const filePath of collectTreeFiles(stagedRoot)) {
    const relative = portablePath(path.relative(stagedRoot, filePath));
    const parts = relative.split("/");
    if (
      CREDENTIAL_PATTERN.test(relative) ||
      parts.some((part) => IGNORED_DIRECTORIES.has(part)) ||
      !relativePathIsAllowed(task, relative)
    ) {
      throw new Error(`staged path is outside the WRITE allowlist: ${relative}`);
    }
    stagedFiles.set(relative, filePath);
  }

  for (const relative of originalFiles) {
    if (!stagedFiles.has(relative)) throw new Error(`staged deletion is forbidden: ${relative}`);
  }

  const pending = [];
  for (const [relative, stagedPath] of [...stagedFiles.entries()].sort()) {
    const destination = path.resolve(task.workspace, relative);
    const stagedBytes = readFileSync(stagedPath);
    const artifact = frozenArtifactForPath(task, relative);
    if (artifact) {
      if (
        stagedBytes.length !== artifact.byte_length ||
        sha256(stagedBytes) !== artifact.sha256
      ) {
        throw new Error(`staged frozen artifact bytes do not match descriptor: ${relative}`);
      }
    } else {
      const content = new TextDecoder("utf-8", { fatal: true }).decode(stagedBytes);
      if (content.length > MAX_WRITE_CHARS) {
        throw new Error("write content exceeds bounded size");
      }
    }
    const originalBytes = existsSync(destination) ? readFileSync(destination) : null;
    if (originalBytes === null || !originalBytes.equals(stagedBytes)) {
      pending.push(Object.freeze({
        relative,
        destination,
        bytes: Buffer.from(stagedBytes),
        staged_sha256: sha256(stagedBytes),
        staged_byte_length: stagedBytes.length,
        frozen_artifact: artifact
          ? Object.freeze({
              artifact_id: artifact.artifact_id,
              path: artifact.path,
              sha256: artifact.sha256,
              byte_length: artifact.byte_length,
            })
          : null,
      }));
    }
  }
  return Object.freeze(pending);
}

function applyStagedTextChangePlan(task, pending) {
  for (const change of pending) {
    archiveExisting(task, change.relative, change.destination);
    mkdirSync(path.dirname(change.destination), { recursive: true });
    writeFileSync(change.destination, change.bytes);
  }
  return pending.map((change) => change.relative);
}

export function applyStagedTextChanges(task, stagedRoot) {
  return applyStagedTextChangePlan(task, collectStagedTextChanges(task, stagedRoot));
}

function stagedApplicationReceipts(pending) {
  return pending.map((change) => {
    let actualSha256 = null;
    let actualByteLength = null;
    let errorCode = null;
    try {
      if (!existsSync(change.destination)) {
        errorCode = "STAGED_APPLICATION_TARGET_MISSING";
      } else if (lstatSync(change.destination).isSymbolicLink()) {
        errorCode = "STAGED_APPLICATION_TARGET_REPARSE";
      } else if (!lstatSync(change.destination).isFile()) {
        errorCode = "STAGED_APPLICATION_TARGET_NOT_REGULAR_FILE";
      } else {
        const bytes = readFileSync(change.destination);
        actualSha256 = sha256(bytes);
        actualByteLength = bytes.length;
        if (
          actualSha256 !== change.staged_sha256 ||
          actualByteLength !== change.staged_byte_length
        ) {
          errorCode = "STAGED_APPLICATION_MISMATCH";
        }
      }
    } catch {
      errorCode = "STAGED_APPLICATION_READ_ERROR";
    }
    return Object.freeze({
      kind: "STAGED_APPLICATION",
      phase: "HOST_POST_APPLY",
      path: change.relative,
      expected_sha256: change.staged_sha256,
      expected_byte_length: change.staged_byte_length,
      actual_sha256: actualSha256,
      actual_byte_length: actualByteLength,
      artifact_id: change.frozen_artifact?.artifact_id ?? null,
      artifact_descriptor_sha256: change.frozen_artifact?.sha256 ?? null,
      artifact_descriptor_byte_length:
        change.frozen_artifact?.byte_length ?? null,
      passed: errorCode === null,
      error_code: errorCode,
    });
  });
}

export function buildLunaInvocation(
  task,
  {
    jobDirectory,
    stagingWorkspace,
    executable,
    fallbackRoute = "LUNA",
  } = {},
) {
  if (!jobDirectory || !stagingWorkspace) throw new Error("Luna invocation paths are required");
  const profile = resolveFallbackProfile(fallbackRoute);
  const routeKey = normalizeFallbackRoute(fallbackRoute).toLowerCase();
  const launch = executable
    ? { executable, prefixArgs: [] }
    : defaultCodexLaunch();
  const schemaPath = path.join(jobDirectory, `${routeKey}-handoff-schema.json`);
  const outputPath = path.join(jobDirectory, `${routeKey}-final.json`);
  atomicJson(schemaPath, handoffToolSchema());
  return {
    executable: launch.executable,
    args: [
      ...launch.prefixArgs,
      "exec",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--model",
      profile.model,
      "--config",
      `model_reasoning_effort="${profile.reasoning}"`,
      "--sandbox",
      task.mode === "READ_ONLY" ? "read-only" : "workspace-write",
      "--cd",
      stagingWorkspace,
      "--ephemeral",
      "--json",
      "--output-schema",
      schemaPath,
      "--output-last-message",
      outputPath,
      "-",
    ],
    cwd: stagingWorkspace,
    env: buildChildEnvironment(process.env),
    prompt: buildLunaWorkerPrompt(task),
    outputPath,
    schemaPath,
  };
}

export function buildSolHeadInvocation(
  plan,
  {
    jobDirectory,
    stagingWorkspace,
    executable,
  } = {},
) {
  assertSolHeadPlan(plan);
  if (!jobDirectory || !stagingWorkspace) throw new Error("Sol head invocation paths are required");
  const launch = executable
    ? { executable, prefixArgs: [] }
    : defaultCodexLaunch();
  const schemaPath = path.join(jobDirectory, "head-handoff-schema.json");
  const outputPath = path.join(jobDirectory, "head-final.json");
  atomicJson(schemaPath, headHandoffSchema());
  return {
    executable: launch.executable,
    args: [
      ...launch.prefixArgs,
      "exec",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--model",
      SOL_HEAD.model,
      "--config",
      `model_reasoning_effort="${plan.route.selected_effort}"`,
      "--sandbox",
      "read-only",
      "--cd",
      stagingWorkspace,
      "--ephemeral",
      "--json",
      "--output-schema",
      schemaPath,
      "--output-last-message",
      outputPath,
      "-",
    ],
    cwd: stagingWorkspace,
    env: buildChildEnvironment(process.env),
    prompt: buildSolHeadPrompt(plan),
    outputPath,
    schemaPath,
  };
}

export async function runCodexProcess(invocation, { signal } = {}) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const child = spawn(invocation.executable, invocation.args, {
      cwd: invocation.cwd,
      env: invocation.env,
      shell: false,
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      signal?.removeEventListener("abort", onAbort);
      callback();
    };
    const onAbort = () => {
      child.kill();
      const error = new Error("Codex Luna process aborted");
      error.name = "AbortError";
      finish(() => reject(error));
    };
    if (signal?.aborted) return onAbort();
    signal?.addEventListener("abort", onAbort, { once: true });
    child.stdout.on("data", (chunk) => {
      stdout = boundedText(`${stdout}${chunk.toString("utf8")}`, MAX_COMMAND_OUTPUT_CHARS);
    });
    child.stderr.on("data", (chunk) => {
      stderr = boundedText(`${stderr}${chunk.toString("utf8")}`, MAX_COMMAND_OUTPUT_CHARS);
    });
    child.on("error", (error) => finish(() => reject(error)));
    child.on("close", (code) =>
      finish(() =>
        resolve({
          exit_code: code ?? 1,
          stdout,
          stderr,
          elapsed_ms: Date.now() - started,
        }),
      ),
    );
    child.stdin.end(invocation.prompt, "utf8");
  });
}

export async function runCodexLunaAgent(
  task,
  {
    jobDirectory,
    processRunner = runCodexProcess,
    signal,
    executable,
    fallbackRoute = "LUNA",
    budgetController = null,
    commandRunner = runApprovedCommand,
  } = {},
) {
  if (task?.localExactWrite === true) {
    const error = new Error("LOCAL exact-byte WRITE is host-only and cannot run through Luna");
    Object.defineProperty(error, "lunaProviderStarted", {
      value: false,
      enumerable: false,
    });
    throw error;
  }
  requireRouteBudgetController(budgetController, fallbackRoute);
  let stagedRoot;
  let stagedTask;
  let beforeFingerprint;
  let invocation;
  try {
    stagedRoot = stageAllowedPaths(task, jobDirectory);
    stagedTask = Object.freeze({ ...task, workspace: stagedRoot });
    beforeFingerprint = await fingerprintAllowedPaths(stagedRoot, task.allowedPaths);
    invocation = buildLunaInvocation(task, {
      jobDirectory,
      stagingWorkspace: stagedRoot,
      executable,
      fallbackRoute,
    });
  } catch (error) {
    const normalized = error instanceof Error ? error : new Error(String(error));
    Object.defineProperty(normalized, "lunaProviderStarted", {
      value: false,
      enumerable: false,
    });
    throw normalized;
  }
  const processResult = await processRunner(invocation, { signal });
  if (processResult.exit_code !== 0) {
    const diagnostic = String(processResult.stderr ?? "").trim()
      ? processResult.stderr
      : processResult.stdout;
    throw new Error(
      `Codex Luna failed (${processResult.exit_code}): ${safeDiagnosticText(diagnostic)}`,
    );
  }
  if (!existsSync(invocation.outputPath)) throw new Error("Codex Luna did not write a final handoff");
  let candidate;
  try {
    candidate = readJson(invocation.outputPath);
  } catch {
    throw new Error("Codex Luna returned malformed final JSON");
  }
  const runtime = { inspectedPaths: [], changedPaths: [], commandsRun: [] };
  let handoff = normalizeHandoff(candidate, stagedTask, runtime);
  const afterFingerprint = await fingerprintAllowedPaths(stagedRoot, task.allowedPaths);
  if (task.mode === "READ_ONLY" && beforeFingerprint !== afterFingerprint) {
    throw new Error("Codex Luna changed files during READ_ONLY work");
  }
  if (task.mode === "WRITE" && handoff.status === "PASS") {
    const pending = collectStagedTextChanges(task, stagedRoot);
    const changedPaths = applyStagedTextChangePlan(task, pending);
    const applicationReceipts = stagedApplicationReceipts(pending);
    handoff.files_changed = changedPaths;
    handoff = await applyHostWriteVerification(handoff, task, {
      changedPaths,
      commandRunner,
      signal,
      stagedApplicationReceipts: applicationReceipts,
    });
  }
  handoff = redactDiagnostic(handoff);
  const profile = resolveFallbackProfile(fallbackRoute);
  return {
    handoff,
    provider: profile.provider,
    model: profile.model,
    reasoning: profile.reasoning,
    chatgpt_subscription: true,
    exit_code: processResult.exit_code,
    elapsed_ms: processResult.elapsed_ms,
    usage: parseCodexJsonUsage(processResult.stdout),
    stdout: safeDiagnosticText(processResult.stdout, [], MAX_COMMAND_OUTPUT_CHARS),
    stderr: safeDiagnosticText(processResult.stderr),
    staging_workspace: stagedRoot,
  };
}

export async function runCodexSolHeadAgent(
  plan,
  {
    jobDirectory,
    processRunner = runCodexProcess,
    signal,
    executable,
    budgetController = null,
  } = {},
) {
  requireRouteBudgetController(budgetController, "SOL");
  let executionTask;
  let stagedRoot;
  let beforeFingerprint;
  let invocation;
  try {
    assertSolHeadPlan(plan);
    executionTask = headExecutionTask(plan);
    const currentEvidenceHash = await fingerprintAllowedPaths(
      executionTask.workspace,
      plan.task.allowedPaths,
    );
    const currentGovernanceHash = await fingerprintAllowedPaths(
      executionTask.workspace,
      plan.governance_paths,
    );
    if (currentEvidenceHash !== plan.evidence_hash) {
      throw new Error("Sol head plan evidence changed after planning");
    }
    if (currentGovernanceHash !== plan.governance_hash) {
      throw new Error("Sol head governance changed after planning");
    }
    stagedRoot = stageAllowedPaths(executionTask, jobDirectory);
    beforeFingerprint = await fingerprintAllowedPaths(stagedRoot, executionTask.allowedPaths);
    invocation = buildSolHeadInvocation(plan, {
      jobDirectory,
      stagingWorkspace: stagedRoot,
      executable,
    });
  } catch (error) {
    const normalized = error instanceof Error ? error : new Error(String(error));
    Object.defineProperty(normalized, "headProviderStarted", {
      value: false,
      enumerable: false,
    });
    throw normalized;
  }
  const processResult = await processRunner(invocation, { signal });
  if (processResult.exit_code !== 0) {
    const diagnostic = String(processResult.stderr ?? "").trim()
      ? processResult.stderr
      : processResult.stdout;
    throw new Error(
      `Codex Sol head failed (${processResult.exit_code}): ${safeDiagnosticText(diagnostic)}`,
    );
  }
  if (!existsSync(invocation.outputPath)) {
    throw new Error("Codex Sol head did not write a final handoff");
  }
  let candidate;
  try {
    candidate = readJson(invocation.outputPath);
  } catch {
    throw new Error("Codex Sol head returned malformed final JSON");
  }
  const handoff = redactDiagnostic(normalizeHeadHandoff(candidate, plan, {
    ...executionTask,
    workspace: stagedRoot,
  }));
  const afterFingerprint = await fingerprintAllowedPaths(stagedRoot, executionTask.allowedPaths);
  if (beforeFingerprint !== afterFingerprint) {
    throw new Error("Codex Sol head changed files during READ_ONLY work");
  }
  return {
    handoff,
    provider: SOL_HEAD.provider,
    model: SOL_HEAD.model,
    requested_effort: plan.route.selected_effort,
    actual_effort: "UNVERIFIED",
    chatgpt_subscription: true,
    exit_code: processResult.exit_code,
    elapsed_ms: processResult.elapsed_ms,
    usage: parseCodexJsonUsage(processResult.stdout),
    stdout: safeDiagnosticText(processResult.stdout, [], MAX_COMMAND_OUTPUT_CHARS),
    stderr: safeDiagnosticText(processResult.stderr),
    staging_workspace: stagedRoot,
  };
}

export function parseCodexJsonUsage(stdout) {
  const usage = {
    input_tokens: 0,
    cached_input_tokens: 0,
    output_tokens: 0,
    reasoning_output_tokens: 0,
    total_tokens: 0,
  };
  for (const line of String(stdout ?? "").split(/\r?\n/)) {
    if (!line.trim()) continue;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      continue;
    }
    if (event?.type !== "turn.completed" || !event.usage) continue;
    usage.input_tokens += Number(event.usage.input_tokens) || 0;
    usage.cached_input_tokens += Number(event.usage.cached_input_tokens) || 0;
    usage.output_tokens += Number(event.usage.output_tokens) || 0;
    usage.reasoning_output_tokens += Number(event.usage.reasoning_output_tokens) || 0;
  }
  // Codex flattens reasoning_tokens beside output_tokens, but reasoning is an output-token subset.
  usage.total_tokens = usage.input_tokens + usage.output_tokens;
  return usage;
}

function functionTool(name, description, parameters) {
  return { type: "function", function: { name, description, parameters } };
}

function packedProviderEvidenceId({
  manifestHash,
  relativePath,
  fileSha256,
  start,
  end,
}) {
  return `EV-${canonicalHash({
    schema_version: 1,
    protocol: "FLASH_PACKED_PROVIDER_EVIDENCE_ID_V1",
    manifest_hash: manifestHash,
    relative_path: relativePath,
    file_sha256: fileSha256,
    start,
    end,
    unit: "line",
  }).slice(0, 32)}`;
}

const FLASH_PACKED_FINDING_FIELDS = Object.freeze([
  "positive_findings",
  "negative_findings",
]);
const FLASH_PACKED_HANDOFF_KEYS = Object.freeze([...HANDOFF_KEYS].sort());
const FLASH_PACKED_WRITE_KEYS = Object.freeze(
  [...HANDOFF_KEYS, "write_operations"].sort(),
);
const FLASH_PACKED_FINDING_KEYS = Object.freeze(["citation", "text"]);
const FLASH_PACKED_NESTED_CITATION_KEYS = Object.freeze([
  "end",
  "evidence_id",
  "start",
  "unit",
]);

function hasExactObjectKeys(value, expectedKeys) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const actual = Object.keys(value).sort();
  return actual.length === expectedKeys.length &&
    actual.every((key, index) => key === expectedKeys[index]);
}

function normalizeFlashPackedCitation(raw, label) {
  if (!hasExactObjectKeys(raw, FLASH_PACKED_NESTED_CITATION_KEYS)) {
    throw new Error(
      `${label} must contain exactly ${FLASH_PACKED_NESTED_CITATION_KEYS.join(", ")}`,
    );
  }
  if (!/^EV-[a-f0-9]{32}$/.test(raw.evidence_id)) {
    throw new Error(`${label}.evidence_id is invalid`);
  }
  if (!Number.isSafeInteger(raw.start) || raw.start < 1) {
    throw new Error(`${label}.start must be a positive integer`);
  }
  if (!Number.isSafeInteger(raw.end) || raw.end < raw.start) {
    throw new Error(`${label}.end must be an integer at least start`);
  }
  if (raw.unit !== "line") throw new Error(`${label}.unit must be line`);
  return { ...raw };
}

function findFlashPackedHandoffCandidate(parsed, requiredKeys, maxDepth = 3) {
  const scan = (value, depth) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    if (hasExactObjectKeys(value, requiredKeys)) return value;
    const keys = Object.keys(value);
    if (requiredKeys.every((key) => keys.includes(key))) {
      return Object.fromEntries(requiredKeys.map((key) => [key, value[key]]));
    }
    if (depth <= 0) return null;
    for (const key of keys) {
      const nested = value[key];
      if (!nested || typeof nested !== "object") continue;
      const found = scan(nested, depth - 1);
      if (found !== null) return found;
    }
    return null;
  };
  return scan(parsed, maxDepth);
}

function materializeFlashPackedHandoff(candidate, packedEvidenceIdMap, {
  tolerant = false,
} = {}) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    throw new Error("Flash packed handoff must be an object");
  }
  if (!hasExactObjectKeys(candidate, FLASH_PACKED_HANDOFF_KEYS)) {
    if (!tolerant) {
      throw new Error(
        `Flash packed handoff must contain exactly ${FLASH_PACKED_HANDOFF_KEYS.join(", ")}`,
      );
    }
    const extracted = findFlashPackedHandoffCandidate(
      candidate,
      FLASH_PACKED_HANDOFF_KEYS,
    );
    if (extracted === null) {
      throw new Error(
        `Flash packed handoff must contain exactly ${FLASH_PACKED_HANDOFF_KEYS.join(", ")}`,
      );
    }
    candidate = extracted;
  }
  const materializeCitation = (citation, label) => {
    const binding = packedEvidenceIdMap.get(citation.evidence_id);
    if (!binding) {
      throw new Error("Flash packed evidence returned an unknown evidence_id");
    }
    if (citation.start < binding.start || citation.end > binding.end) {
      throw new Error(`${label} is outside the receipted range`);
    }
    return {
      ...citation,
      evidence_id: binding.evidence_id,
    };
  };
  const findings = {};
  const citations = [];

  for (const findingField of FLASH_PACKED_FINDING_FIELDS) {
    const rawFindings = candidate[findingField];
    if (!Array.isArray(rawFindings)) {
      throw new Error(`Flash packed ${findingField} must be an array`);
    }
    findings[findingField] = rawFindings.map((item, findingIndex) => {
      const label = `Flash packed ${findingField}[${findingIndex}]`;
      if (!hasExactObjectKeys(item, FLASH_PACKED_FINDING_KEYS)) {
        throw new Error(
          `${label} must contain exactly ${FLASH_PACKED_FINDING_KEYS.join(", ")}`,
        );
      }
      if (typeof item.text !== "string" || !item.text.trim()) {
        throw new Error(`${label}.text must be a non-empty string`);
      }
      const citation = normalizeFlashPackedCitation(
        item.citation,
        `${label}.citation`,
      );
      citations.push({
        finding_field: findingField,
        finding_index: findingIndex,
        ...materializeCitation(citation, `${label}.citation`),
      });
      return item.text;
    });
  }

  return {
    ...candidate,
    ...findings,
    citations,
  };
}

function materializeFlashPackedWritePlan(
  candidate,
  packedEvidenceIdMap,
  task,
  {
    tolerant = false,
  } = {},
) {
  if (!hasExactObjectKeys(candidate, FLASH_PACKED_WRITE_KEYS)) {
    if (!tolerant) {
      throw new Error(
        `Flash packed WRITE must contain exactly ${FLASH_PACKED_WRITE_KEYS.join(", ")}`,
      );
    }
    const extracted = findFlashPackedHandoffCandidate(
      candidate,
      FLASH_PACKED_WRITE_KEYS,
    );
    if (extracted === null) {
      throw new Error(
        `Flash packed WRITE must contain exactly ${FLASH_PACKED_WRITE_KEYS.join(", ")}`,
      );
    }
    candidate = extracted;
  }
  if (!Array.isArray(candidate.write_operations) || candidate.write_operations.length > 8) {
    throw new Error("Flash packed WRITE operations must be an array of at most 8 items");
  }
  const frozenArtifacts = task.frozenArtifacts ?? [];
  const frozenById = new Map(
    frozenArtifacts.map((artifact) => [artifact.artifact_id, artifact]),
  );
  const frozenPathIdentities = new Set(
    frozenArtifacts.map((artifact) => writeVerificationPathIdentity(artifact.path)),
  );
  const referencedFrozenIds = new Set();
  const operationPathCounts = new Map();
  const writeOperations = candidate.write_operations.map((operation, index) => {
    const label = `Flash packed WRITE operation[${index}]`;
    if (!operation || typeof operation !== "object" || Array.isArray(operation)) {
      throw new Error(`${label} must be an object`);
    }
    let operationPath;
    try {
      operationPath = normalizeAllowedPath(task.workspace, operation.path);
    } catch {
      throw new Error(`${label}.path is outside the exact WRITE allowlist`);
    }
    if (!relativePathIsAllowed(task, operationPath)) {
      throw new Error(`${label}.path is outside the exact WRITE allowlist`);
    }
    const pathIdentity = writeVerificationPathIdentity(operationPath);
    operationPathCounts.set(pathIdentity, (operationPathCounts.get(pathIdentity) ?? 0) + 1);
    if (
      operationPathCounts.get(pathIdentity) > 1 &&
      frozenPathIdentities.has(pathIdentity)
    ) {
      throw new Error(`${label} duplicates a frozen artifact mutation path`);
    }
    if (operation.kind === "replace_text") {
      if (!hasExactObjectKeys(operation, ["kind", "new_text", "old_text", "path"])) {
        throw new Error(`${label} has invalid replace_text keys`);
      }
      if (
        typeof operation.old_text !== "string" ||
        operation.old_text.length < 1 ||
        typeof operation.new_text !== "string"
      ) {
        throw new Error(`${label} has invalid replace_text content`);
      }
    } else if (operation.kind === "write_file") {
      if (!hasExactObjectKeys(operation, ["content", "kind", "path"])) {
        throw new Error(`${label} has invalid write_file keys`);
      }
      if (typeof operation.content !== "string") {
        throw new Error(`${label}.content must be a string`);
      }
    } else if (operation.kind === "write_frozen_file") {
      if (!hasExactObjectKeys(
        operation,
        ["artifact_id", "byte_length", "kind", "path", "sha256"],
      )) {
        throw new Error(`${label} has invalid write_frozen_file keys`);
      }
      if (frozenArtifacts.length === 0) {
        throw new Error(`${label} requires a frozen_artifacts task table`);
      }
      const artifact = frozenById.get(operation.artifact_id);
      if (!artifact) {
        throw new Error(`${label} references an unknown frozen artifact`);
      }
      if (referencedFrozenIds.has(artifact.artifact_id)) {
        throw new Error(`${label} is a duplicate frozen artifact reference`);
      }
      if (operationPath !== artifact.path) {
        throw new Error(`${label} path does not match the frozen artifact descriptor`);
      }
      if (operation.sha256 !== artifact.sha256) {
        throw new Error(`${label} SHA-256 does not match the frozen artifact descriptor`);
      }
      if (operation.byte_length !== artifact.byte_length) {
        throw new Error(`${label} byte length does not match the frozen artifact descriptor`);
      }
      referencedFrozenIds.add(artifact.artifact_id);
    } else {
      throw new Error(`${label}.kind is unsupported`);
    }
    const contentLength = operation.kind === "replace_text"
      ? Math.max(operation.old_text.length, operation.new_text.length)
      : operation.kind === "write_file"
        ? operation.content.length
        : operation.byte_length;
    if (contentLength > MAX_WRITE_CHARS) {
      throw new Error(`${label} content exceeds the safe limit`);
    }
    return Object.freeze({ ...operation, path: operationPath });
  });
  for (const artifact of frozenArtifacts) {
    if (!referencedFrozenIds.has(artifact.artifact_id)) {
      throw new Error(
        `Flash packed WRITE has an unreferenced frozen artifact: ${artifact.artifact_id}`,
      );
    }
  }
  const handoffCandidate = Object.fromEntries(
    HANDOFF_KEYS.map((key) => [key, candidate[key]]),
  );
  return Object.freeze({
    handoff: materializeFlashPackedHandoff(
      handoffCandidate,
      packedEvidenceIdMap,
    ),
    writeOperations: Object.freeze(writeOperations),
  });
}

function captureFlashWriteRollbackSnapshot(task) {
  const files = new Map();
  const directories = new Set();
  const roots = [...new Set([
    ...task.allowedPaths,
    ...(task.requiredReads ?? []).map((read) => read.path),
  ])];
  const visit = (fullPath) => {
    if (pathContainsReparsePoint(task.workspace, fullPath)) {
      throw new Error(`Flash WRITE rollback snapshot found a reparse path: ${fullPath}`);
    }
    const metadata = lstatSync(fullPath);
    const relative = portablePath(path.relative(task.workspace, fullPath));
    if (metadata.isFile()) {
      files.set(relative, Object.freeze({
        relative,
        fullPath,
        bytes: Buffer.from(readFileSync(fullPath)),
      }));
      return;
    }
    if (!metadata.isDirectory()) {
      throw new Error(`Flash WRITE rollback snapshot found a non-file path: ${relative}`);
    }
    directories.add(relative);
    for (const entry of readdirSync(fullPath, { withFileTypes: true })) {
      if (IGNORED_DIRECTORIES.has(entry.name)) continue;
      visit(path.join(fullPath, entry.name));
    }
  };
  for (const relativeRoot of roots) {
    const target = relativePathIsAllowed(task, relativeRoot)
      ? resolveToolPath(task, relativeRoot)
      : resolveRequiredReadPath(task, relativeRoot);
    if (!existsSync(target.fullPath)) {
      throw new Error(`Flash WRITE rollback root is missing: ${relativeRoot}`);
    }
    visit(target.fullPath);
  }
  const archiveRoot = path.join(task.workspace, ".archive");
  return Object.freeze({
    files,
    directories,
    roots: Object.freeze(roots),
    archiveRoot,
    archiveRootExisted: existsSync(archiveRoot),
    archiveEntries: existsSync(archiveRoot)
      ? new Set(readdirSync(archiveRoot))
      : new Set(),
  });
}

function restoreFlashWriteRollbackSnapshot(task, snapshot) {
  if (
    !snapshot ||
    !(snapshot.files instanceof Map) ||
    !(snapshot.directories instanceof Set) ||
    !Array.isArray(snapshot.roots)
  ) {
    throw new Error("Flash WRITE rollback snapshot is unavailable");
  }
  const currentFiles = new Set();
  const currentDirectories = new Set();
  const visitCurrent = (fullPath) => {
    if (pathContainsReparsePoint(task.workspace, fullPath)) {
      throw new Error(`Flash WRITE rollback found a reparse path: ${fullPath}`);
    }
    const metadata = lstatSync(fullPath);
    const relative = portablePath(path.relative(task.workspace, fullPath));
    if (metadata.isFile()) {
      currentFiles.add(relative);
      return;
    }
    if (!metadata.isDirectory()) {
      throw new Error(`Flash WRITE rollback found a non-file path: ${relative}`);
    }
    currentDirectories.add(relative);
    for (const entry of readdirSync(fullPath, { withFileTypes: true })) {
      if (IGNORED_DIRECTORIES.has(entry.name)) continue;
      visitCurrent(path.join(fullPath, entry.name));
    }
  };
  for (const relativeRoot of snapshot.roots) {
    const fullRoot = path.resolve(task.workspace, relativeRoot);
    if (!isWithin(task.workspace, fullRoot)) {
      throw new Error(`Flash WRITE rollback root escaped the workspace: ${relativeRoot}`);
    }
    if (existsSync(fullRoot)) visitCurrent(fullRoot);
  }
  for (const record of snapshot.files.values()) {
    const expected = path.resolve(task.workspace, record.relative);
    if (
      expected !== record.fullPath ||
      !isWithin(task.workspace, expected) ||
      pathContainsReparsePoint(task.workspace, expected)
    ) {
      throw new Error(`Flash WRITE rollback target is unsafe: ${record.relative}`);
    }
  }
  for (const relative of [...currentFiles].sort().reverse()) {
    if (snapshot.files.has(relative)) continue;
    const candidate = path.resolve(task.workspace, relative);
    if (
      !isWithin(task.workspace, candidate) ||
      pathContainsReparsePoint(task.workspace, candidate) ||
      !lstatSync(candidate).isFile()
    ) {
      throw new Error(`Flash WRITE rollback new file is unsafe: ${relative}`);
    }
    rmSync(candidate, { force: true });
  }
  for (
    const relative of [...currentDirectories]
      .filter((entry) => !snapshot.directories.has(entry))
      .sort((left, right) => right.split("/").length - left.split("/").length)
  ) {
    const candidate = path.resolve(task.workspace, relative);
    if (
      !isWithin(task.workspace, candidate) ||
      pathContainsReparsePoint(task.workspace, candidate)
    ) {
      throw new Error(`Flash WRITE rollback new directory is unsafe: ${relative}`);
    }
    rmSync(candidate, { recursive: true, force: true });
  }
  for (const relative of snapshot.directories) {
    const candidate = path.resolve(task.workspace, relative);
    if (!isWithin(task.workspace, candidate)) {
      throw new Error(`Flash WRITE rollback directory is unsafe: ${relative}`);
    }
    mkdirSync(candidate, { recursive: true });
  }
  for (const record of snapshot.files.values()) {
    mkdirSync(path.dirname(record.fullPath), { recursive: true });
    writeFileSync(record.fullPath, record.bytes);
  }
  if (existsSync(snapshot.archiveRoot)) {
    for (const entry of readdirSync(snapshot.archiveRoot)) {
      if (snapshot.archiveEntries.has(entry)) continue;
      const candidate = path.join(snapshot.archiveRoot, entry);
      if (
        path.dirname(candidate) !== snapshot.archiveRoot ||
        lstatSync(candidate).isSymbolicLink() ||
        !lstatSync(candidate).isFile()
      ) {
        throw new Error("Flash WRITE rollback found an unsafe archive artifact");
      }
      rmSync(candidate, { force: true });
    }
    if (
      !snapshot.archiveRootExisted &&
      readdirSync(snapshot.archiveRoot).length === 0
    ) {
      rmSync(snapshot.archiveRoot, { recursive: true, force: true });
    }
  }
  for (const record of snapshot.files.values()) {
    if (
      !existsSync(record.fullPath) ||
      pathContainsReparsePoint(task.workspace, record.fullPath) ||
      sha256(readFileSync(record.fullPath)) !== sha256(record.bytes)
    ) {
      throw new Error(`Flash WRITE rollback verification failed: ${record.relative}`);
    }
  }
  const restored = captureFlashWriteRollbackSnapshot(task);
  if (
    restored.files.size !== snapshot.files.size ||
    restored.directories.size !== snapshot.directories.size ||
    [...snapshot.directories].some((relative) => !restored.directories.has(relative)) ||
    [...snapshot.files].some(
      ([relative, record]) =>
        !restored.files.has(relative) ||
        sha256(restored.files.get(relative).bytes) !== sha256(record.bytes),
    ) ||
    restored.archiveRootExisted !== snapshot.archiveRootExisted ||
    restored.archiveEntries.size !== snapshot.archiveEntries.size ||
    [...snapshot.archiveEntries].some((entry) => !restored.archiveEntries.has(entry))
  ) {
    throw new Error("Flash WRITE rollback protected-set verification failed");
  }
  return true;
}

function resolveFrozenArtifactReference(task, operation) {
  const artifact = (task.frozenArtifacts ?? []).find(
    (candidate) => candidate.artifact_id === operation.artifact_id,
  );
  if (!artifact) throw new Error("write_frozen_file references an unknown frozen artifact");
  if (
    operation.path !== artifact.path ||
    operation.sha256 !== artifact.sha256 ||
    operation.byte_length !== artifact.byte_length
  ) {
    throw new Error("write_frozen_file descriptor changed after validation");
  }
  return Object.freeze({
    descriptor: artifact,
    bytes: decodeFrozenArtifactPayload(
      artifact,
      `frozen_artifacts[${artifact.artifact_id}]`,
    ),
  });
}

async function applyFlashPackedWritePlan(
  task,
  writeOperations,
  { commandRunner, signal, assertRequiredReadsFresh } = {},
) {
  const temporaryRoot = mkdtempSync(
    path.join(os.tmpdir(), "deepluna-flash-write-"),
  );
  try {
    const stagedRoot = stageAllowedPaths(task, temporaryRoot);
    const stagedTask = Object.freeze({
      ...task,
      workspace: stagedRoot,
      packedEvidenceMode: null,
      requiredReads: [],
    });
    const stagedRuntime = createRepositoryTools(stagedTask, {
      commandRunner,
      signal,
    });
    for (const operation of writeOperations) {
      const { kind, ...args } = operation;
      if (kind === "write_frozen_file") {
        const resolved = resolveFrozenArtifactReference(task, operation);
        const target = resolveToolPath(stagedTask, resolved.descriptor.path);
        if (
          pathContainsReparsePoint(stagedRoot, target.fullPath) ||
          (
            existsSync(target.fullPath) &&
            (
              !lstatSync(target.fullPath).isFile() ||
              lstatSync(target.fullPath).nlink !== 1
            )
          )
        ) {
          throw new Error(
            `staged frozen artifact target is unsafe: ${resolved.descriptor.path}`,
          );
        }
        mkdirSync(path.dirname(target.fullPath), { recursive: true });
        writeFileSync(target.fullPath, resolved.bytes);
      } else {
        await stagedRuntime.execute(kind, args);
      }
    }
    rmSync(path.join(stagedRoot, ".archive"), {
      recursive: true,
      force: true,
    });
    const pending = collectStagedTextChanges(task, stagedRoot);
    if (signal?.aborted) {
      const error = new Error("Flash WRITE was cancelled before staged commit");
      error.name = "AbortError";
      throw error;
    }
    if (typeof assertRequiredReadsFresh !== "function") {
      throw new Error("Flash WRITE requires an immutable-read pre-commit verifier");
    }
    assertRequiredReadsFresh();
    for (const change of pending) {
      const target = resolveToolPath(task, change.relative);
      if (
        target.fullPath !== change.destination ||
        pathContainsReparsePoint(task.workspace, target.fullPath) ||
        (
          existsSync(target.fullPath) &&
          (
            !lstatSync(target.fullPath).isFile() ||
            lstatSync(target.fullPath).nlink !== 1
          )
        )
      ) {
        throw new Error(
          `staged commit target is not a regular WRITE-allowlisted file: ${change.relative}`,
        );
      }
    }
    const changedPaths = applyStagedTextChangePlan(task, pending);
    return Object.freeze({
      changedPaths: Object.freeze(changedPaths),
      applicationReceipts: Object.freeze(stagedApplicationReceipts(pending)),
    });
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
}

export function createRepositoryTools(
  task,
  { commandRunner = runApprovedCommand, signal, evidenceContext = null } = {},
) {
  const changedPaths = [];
  const inspectedPaths = [];
  const commandsRun = [];
  const receipts = [];
  const packedEvidenceIdMap = new Map();
  const record = (array, value) => {
    if (!array.includes(value)) array.push(value);
  };
  const evidenceState = () => {
    if (!evidenceContext) {
      return { manifest: null, coverageSpec: null, receipts: [...receipts] };
    }
    if (typeof evidenceContext.persistedStateSource !== "function") {
      return {
        manifest: evidenceContext.manifest,
        coverageSpec: task.coverageSpec,
        receipts: [...receipts],
      };
    }
    try {
      const persisted = evidenceContext.persistedStateSource();
      const manifestMatches = stableJson(persisted.manifest) === stableJson(evidenceContext.manifest);
      const coverageMatches = stableJson(persisted.coverageSpec) === stableJson(task.coverageSpec);
      return {
        manifest: manifestMatches
          ? persisted.manifest
          : { ...evidenceContext.manifest, manifest_hash: "PERSISTED_MANIFEST_MISMATCH" },
        coverageSpec: coverageMatches ? persisted.coverageSpec : null,
        receipts: persisted.receipts,
      };
    } catch {
      return {
        manifest: { ...evidenceContext.manifest, manifest_hash: "PERSISTED_CONTEXT_INVALID" },
        coverageSpec: null,
        receipts: [],
      };
    }
  };
  const definitions = [
    functionTool("list_files", "List bounded files below an allowed file or directory.", {
      type: "object",
      properties: { path: { type: "string" } },
      required: ["path"],
      additionalProperties: false,
    }),
    functionTool("read_file", "Read a bounded UTF-8 line range from an allowed file.", {
      type: "object",
      properties: {
        path: { type: "string" },
        start_line: { type: "integer", minimum: 1 },
        end_line: { type: "integer", minimum: 1 },
      },
      required: ["path"],
      additionalProperties: false,
    }),
    functionTool("search_text", "Search literal text under an allowed file or directory.", {
      type: "object",
      properties: {
        path: { type: "string" },
        query: { type: "string" },
        max_results: { type: "integer", minimum: 1, maximum: MAX_SEARCH_RESULTS },
      },
      required: ["path", "query"],
      additionalProperties: false,
    }),
  ];
  if (task.commandsTests.length > 0 && task.mode !== "WRITE") {
    definitions.push(
      functionTool("run_command", "Run one exact command from commands_tests.", {
        type: "object",
        properties: { command: { type: "string", enum: [...task.commandsTests] } },
        required: ["command"],
        additionalProperties: false,
      }),
    );
  }
  if (task.mode === "WRITE" && task.localExactWrite !== true) {
    definitions.push(
      functionTool("replace_text", "Replace one exact text occurrence in an allowed file.", {
        type: "object",
        properties: {
          path: { type: "string" },
          old_text: { type: "string" },
          new_text: { type: "string" },
        },
        required: ["path", "old_text", "new_text"],
        additionalProperties: false,
      }),
      functionTool("write_file", "Write UTF-8 content to an explicitly allowed file.", {
        type: "object",
        properties: { path: { type: "string" }, content: { type: "string" } },
        required: ["path", "content"],
        additionalProperties: false,
      }),
    );
  }
  definitions.push(
    functionTool("finish_handoff", "Return the final bounded evidence handoff to Sol.", handoffToolSchema()),
  );

  const execute = async (name, rawArguments = {}) => {
    const args = rawArguments && typeof rawArguments === "object" ? rawArguments : {};
    if (name === "list_files") {
      const files = enumerateFiles(task, args.path);
      record(inspectedPaths, portablePath(args.path));
      return { files, truncated: files.length >= MAX_LIST_FILES };
    }
    if (name === "read_file") {
      const target = resolveReadableToolPath(task, args.path);
      const manifested = evidenceContext?.manifest?.files?.some(
        (file) => file.relative_path === target.relative,
      );
      if (manifested) {
        assertManifestFresh(evidenceContext.manifest, {
          resolvePath: (relative) =>
            resolveRequiredReadPath(task, relative).fullPath,
        });
      }
      const content = manifested
        ? new TextDecoder("utf-8", { fatal: true }).decode(readFileSync(target.fullPath))
        : readTextFile(target.fullPath);
      const lines = content.replace(/\r\n?/g, "\n").split("\n");
      const start = Number(args.start_line ?? 1);
      const end = Number(args.end_line ?? Math.min(lines.length, start + MAX_READ_LINES - 1));
      if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start) {
        throw new Error("invalid read line range");
      }
      if (end - start + 1 > MAX_READ_LINES) throw new Error("read exceeds maximum line range");
      if (start > lines.length) throw new Error("read starts outside the file line range");
      const boundedEnd = Math.min(end, lines.length);
      if (
        task.mode === "WRITE" &&
        !relativePathIsAllowed(task, target.relative) &&
        !task.requiredReads.some(
          (read) =>
            read.path === target.relative &&
            start >= read.start &&
            boundedEnd <= (read.end ?? lines.length),
        )
      ) {
        throw new Error(
          `read range is outside the declared immutable required_reads scope: ${target.relative}`,
        );
      }
      const selectedContent = lines.slice(start - 1, boundedEnd).join("\n");
      if (manifested && selectedContent.length > MAX_TOOL_RESULT_CHARS) {
        throw new Error("manifested read content is too large; request a smaller line range");
      }
      record(inspectedPaths, target.relative);
      let receipt = null;
      if (manifested) {
        receipt = createReadReceipt({
          manifest: evidenceContext.manifest,
          jobId: evidenceContext.jobId,
          workspaceInstanceId: evidenceContext.workspaceInstanceId,
          relativePath: target.relative,
          start,
          end: boundedEnd,
        });
        receipts.push(receipt);
        evidenceContext.receiptSink?.(receipt);
      }
      return {
        path: target.relative,
        start_line: start,
        end_line: boundedEnd,
        total_lines: lines.length,
        content: manifested ? selectedContent : boundedText(selectedContent),
        evidence_id: receipt?.evidence_id ?? null,
        receipt,
      };
    }
    if (name === "search_text") {
      const query = String(args.query ?? "");
      if (!query || query.length > 500) throw new Error("search query must contain 1 to 500 characters");
      const maximum = Math.min(Number(args.max_results ?? 50), MAX_SEARCH_RESULTS);
      if (!Number.isInteger(maximum) || maximum < 1) throw new Error("invalid max_results");
      const files = enumerateFiles(task, args.path);
      const matches = [];
      for (const relative of files) {
        if (matches.length >= maximum) break;
        try {
          const target = resolveToolPath(task, relative);
          const content = readTextFile(target.fullPath);
          for (const [index, line] of content.split(/\r?\n/).entries()) {
            if (line.toLocaleLowerCase().includes(query.toLocaleLowerCase())) {
              matches.push({ path: relative, line: index + 1, text: boundedText(line, 500) });
              if (matches.length >= maximum) break;
            }
          }
        } catch {
          // Binary and oversized files are skipped rather than exposed.
        }
      }
      record(inspectedPaths, portablePath(args.path));
      return { matches, truncated: matches.length >= maximum };
    }
    if (name === "run_command") {
      if (task.mode === "WRITE") {
        throw new Error("run_command is host-only for WRITE jobs");
      }
      const command = String(args.command ?? "").trim();
      if (!task.commandsTests.includes(command)) throw new Error("command is not approved");
      assertProviderCommandSafety(command, task.mode);
      const result = await commandRunner(command, {
        cwd: task.workspace,
        timeoutMs: Math.min(task.timeoutMs, 300_000),
        signal,
      });
      record(commandsRun, command);
      return {
        exit_code: Number(result.exit_code ?? 1),
        stdout: boundedText(result.stdout, MAX_COMMAND_OUTPUT_CHARS),
        stderr: boundedText(result.stderr, MAX_COMMAND_OUTPUT_CHARS),
      };
    }
    if (name === "replace_text" || name === "write_file") {
      if (task.localExactWrite === true) {
        throw new Error(`${name} is host-only for LOCAL exact-byte WRITE`);
      }
      if (task.mode !== "WRITE") throw new Error(`${name} is WRITE only`);
      const target = resolveToolPath(task, args.path);
      let content;
      if (name === "replace_text") {
        if (!existsSync(target.fullPath)) throw new Error("replace_text target does not exist");
        const current = readTextFile(target.fullPath);
        const oldText = String(args.old_text ?? "");
        if (!oldText) throw new Error("old_text must not be empty");
        if (current.split(oldText).length - 1 !== 1) {
          throw new Error("old_text must occur exactly once");
        }
        content = current.replace(oldText, String(args.new_text ?? ""));
      } else {
        content = String(args.content ?? "");
      }
      if (content.length > MAX_WRITE_CHARS) throw new Error("write content exceeds safe limit");
      const archivePath = archiveExisting(task, target.relative, target.fullPath);
      mkdirSync(path.dirname(target.fullPath), { recursive: true });
      writeFileSync(target.fullPath, content, "utf8");
      record(changedPaths, target.relative);
      if (archivePath) record(changedPaths, archivePath);
      return { changed_path: target.relative, archive_path: archivePath, bytes: Buffer.byteLength(content) };
    }
    if (name === "finish_handoff") return args;
    throw new Error(`unknown repository tool: ${name}`);
  };

  const packRequiredEvidence = () => {
    if (!new Set([
      GLM_PACKED_EVIDENCE_MODE,
      FLASH_PACKED_EVIDENCE_MODE,
      FLASH_PACKED_WRITE_MODE,
    ]).has(task.packedEvidenceMode)) {
      throw new Error("packed evidence is not enabled for this task");
    }
    if (!evidenceContext?.manifest) {
      throw new Error("packed evidence requires a persisted input manifest");
    }
    if (task.requiredReads.length > MAX_GLM_PACKED_SECTIONS) {
      throw new Error(
        `packed evidence exceeds ${MAX_GLM_PACKED_SECTIONS} required ranges`,
      );
    }
    const state = evidenceState();
    if (!state.coverageSpec) {
      throw new Error("packed evidence coverage specification is unavailable or stale");
    }
    assertManifestFresh(state.manifest, {
      resolvePath: (relative) => resolveRequiredReadPath(task, relative).fullPath,
    });
    const sections = [];
    for (const read of task.requiredReads) {
      const file = state.manifest.files.find((entry) => entry.relative_path === read.path);
      if (!file) throw new Error(`required evidence is absent from manifest: ${read.path}`);
      const end = read.end ?? file.line_count;
      const declared = file.required_ranges.some(
        (range) => range.start === read.start && range.end === end && range.unit === "line",
      );
      if (!declared) {
        throw new Error(`required range is not bound to manifest: ${read.path}`);
      }
      const target = resolveRequiredReadPath(task, read.path);
      const content = new TextDecoder("utf-8", { fatal: true }).decode(
        readFileSync(target.fullPath),
      );
      const lines = content.replace(/\r\n?/g, "\n").split("\n");
      const receipt = createReadReceipt({
        manifest: state.manifest,
        jobId: evidenceContext.jobId,
        workspaceInstanceId: evidenceContext.workspaceInstanceId,
        relativePath: read.path,
        start: read.start,
        end,
      });
      receipts.push(receipt);
      evidenceContext.receiptSink?.(receipt);
      record(inspectedPaths, read.path);
      const providerEvidenceId =
      new Set([
        FLASH_PACKED_EVIDENCE_MODE,
        FLASH_PACKED_WRITE_MODE,
      ]).has(task.packedEvidenceMode)
          ? packedProviderEvidenceId({
              manifestHash: state.manifest.manifest_hash,
              relativePath: read.path,
              fileSha256: file.file_sha256,
              start: read.start,
              end,
            })
          : receipt.evidence_id;
      if (new Set([
        FLASH_PACKED_EVIDENCE_MODE,
        FLASH_PACKED_WRITE_MODE,
      ]).has(task.packedEvidenceMode)) {
        const prior = packedEvidenceIdMap.get(providerEvidenceId);
        if (
          prior !== undefined &&
          (
            prior.evidence_id !== receipt.evidence_id ||
            prior.start !== read.start ||
            prior.end !== end
          )
        ) {
          throw new Error("packed evidence identity collision");
        }
        packedEvidenceIdMap.set(providerEvidenceId, Object.freeze({
          evidence_id: receipt.evidence_id,
          start: read.start,
          end,
        }));
      }
      sections.push(Object.freeze({
        evidence_id: providerEvidenceId,
        relative_path: read.path,
        file_sha256: file.file_sha256,
        start: read.start,
        end,
        lines: Object.freeze(
          lines.slice(read.start - 1, end).map(
            (line, index) => `${read.start + index}\t${line}`,
          ),
        ),
      }));
    }
    const core = Object.freeze({
      schema_version: 1,
      protocol: task.packedEvidenceMode,
      manifest_hash: state.manifest.manifest_hash,
      sections: Object.freeze(sections),
    });
    return Object.freeze({ ...core, pack_hash: canonicalHash(core) });
  };
  const tolerantPackedHandoff =
    task.requestDialect === "deepseek";
  const materializePackedHandoff = (candidate) => {
    if (task.packedEvidenceMode !== FLASH_PACKED_EVIDENCE_MODE) return candidate;
    return materializeFlashPackedHandoff(candidate, packedEvidenceIdMap, {
      tolerant: tolerantPackedHandoff,
    });
  };
  const materializePackedWritePlan = (candidate) => {
    if (task.packedEvidenceMode !== FLASH_PACKED_WRITE_MODE) {
      throw new Error("Flash packed WRITE is not enabled for this task");
    }
    return materializeFlashPackedWritePlan(
      candidate,
      packedEvidenceIdMap,
      task,
      { tolerant: tolerantPackedHandoff },
    );
  };
  const assertRequiredEvidenceFresh = () => {
    const state = evidenceState();
    if (!state.manifest) {
      throw new Error("required evidence manifest is unavailable or stale");
    }
    assertManifestFresh(state.manifest, {
      resolvePath: (relative) => resolveRequiredReadPath(task, relative).fullPath,
    });
    return state.manifest.manifest_hash;
  };

  return {
    definitions,
    execute,
    changedPaths,
    inspectedPaths,
    commandsRun,
    receipts,
    evidenceState,
    assertRequiredEvidenceFresh,
    packRequiredEvidence,
    materializePackedHandoff,
    materializePackedWritePlan,
  };
}

export const WRITE_VERIFICATION_FAILED = "WRITE_VERIFICATION_FAILED";

function writeVerificationChangedPaths(changedPaths = []) {
  return [...new Set(
    changedPaths
      .map((relative) => portablePath(String(relative ?? "")))
      .filter((relative) => relative && relative !== ".archive" && !relative.startsWith(".archive/")),
  )];
}

function pathContainsReparsePoint(workspace, fullPath) {
  const relative = path.relative(workspace, fullPath);
  if (!relative) return lstatSync(fullPath).isSymbolicLink();
  let current = workspace;
  for (const part of relative.split(path.sep)) {
    current = path.join(current, part);
    if (existsSync(current) && lstatSync(current).isSymbolicLink()) return true;
  }
  return false;
}

function commandReceiptTest(receipt) {
  return [
    "HOST_POST_WRITE",
    receipt.passed ? "PASS" : "FAIL",
    `command_sha256=${receipt.command_sha256}`,
    `exit_code=${receipt.exit_code}`,
    `workspace_unchanged=${receipt.workspace_unchanged}`,
  ].join(" ");
}

function fileReceiptTest(receipt) {
  return [
    "HOST_FILE_BYTES",
    receipt.passed ? "PASS" : "FAIL",
    `path=${receipt.path}`,
    `sha256=${receipt.actual_sha256 ?? "UNAVAILABLE"}`,
    `byte_length=${receipt.actual_byte_length ?? "UNAVAILABLE"}`,
  ].join(" ");
}

export async function verifyWriteCompletion(
  task,
  {
    changedPaths = [],
    commandRunner = runApprovedCommand,
    signal,
    stagedApplicationReceipts = [],
  } = {},
) {
  if (task.mode !== "WRITE") throw new Error("host WRITE verification requires WRITE mode");
  const commands = Array.isArray(task.commandsTests) ? task.commandsTests : [];
  const exact = Array.isArray(task.writeVerifications) ? task.writeVerifications : [];
  const changedTargets = writeVerificationChangedPaths(changedPaths);
  const receipts = [...stagedApplicationReceipts];
  const errors = stagedApplicationReceipts
    .filter((receipt) => receipt?.passed === false)
    .map((receipt) => receipt.error_code ?? "STAGED_APPLICATION_MISMATCH");
  const commandsRun = [];
  const verifierProtectedPaths = [...new Set([
    ...task.allowedPaths,
    ...(task.requiredReads ?? []).map((read) => read.path),
  ])];

  if (commands.length === 0 && exact.length === 0) {
    errors.push("MISSING_HOST_WRITE_VERIFIER");
  }

  for (const command of commands) {
    let beforeFingerprint = null;
    let afterFingerprint = null;
    let exitCode = null;
    let stdout = "";
    let stderr = "";
    let runnerError = null;
    try {
      assertProviderCommandSafety(command, task.mode);
      beforeFingerprint = await fingerprintAllowedPaths(
        task.workspace,
        verifierProtectedPaths,
      );
      const completed = await commandRunner(command, {
        cwd: task.workspace,
        timeoutMs: Math.min(task.timeoutMs, 300_000),
        signal,
      });
      const rawExitCode = completed?.exit_code ?? completed?.exitCode;
      exitCode = Number.isSafeInteger(Number(rawExitCode)) ? Number(rawExitCode) : 1;
      stdout = String(completed?.stdout ?? "");
      stderr = String(completed?.stderr ?? "");
    } catch (error) {
      runnerError = error;
    }
    try {
      afterFingerprint = await fingerprintAllowedPaths(
        task.workspace,
        verifierProtectedPaths,
      );
    } catch (error) {
      runnerError ??= error;
    }
    const workspaceUnchanged =
      beforeFingerprint !== null &&
      afterFingerprint !== null &&
      beforeFingerprint === afterFingerprint;
    const passed = runnerError === null && exitCode === 0 && workspaceUnchanged;
    const receipt = Object.freeze({
      kind: "COMMAND",
      phase: "HOST_POST_WRITE",
      command,
      command_sha256: sha256(command),
      exit_code: exitCode,
      stdout_sha256: sha256(stdout),
      stderr_sha256: sha256(stderr),
      stdout_byte_length: Buffer.byteLength(stdout, "utf8"),
      stderr_byte_length: Buffer.byteLength(stderr, "utf8"),
      before_fingerprint: beforeFingerprint,
      after_fingerprint: afterFingerprint,
      workspace_unchanged: workspaceUnchanged,
      passed,
      error_code: runnerError
        ? "COMMAND_RUNNER_ERROR"
        : exitCode !== 0
          ? "COMMAND_EXIT_NONZERO"
          : workspaceUnchanged
            ? null
            : "VERIFIER_MUTATED_WORKSPACE",
    });
    receipts.push(receipt);
    commandsRun.push(command);
    if (!passed) errors.push(receipt.error_code);
  }

  const exactIdentities = new Set(
    exact.map((verification) => writeVerificationPathIdentity(verification.path)),
  );
  if (
    commands.length === 0 &&
    changedTargets.some(
      (relative) => !exactIdentities.has(writeVerificationPathIdentity(relative)),
    )
  ) {
    errors.push("UNVERIFIED_CHANGED_PATH");
  }

  const canonicalWorkspace = realpathSync.native(task.workspace);
  for (const verification of exact) {
    let actualSha256 = null;
    let actualByteLength = null;
    let errorCode = null;
    try {
      const target = resolveToolPath(task, verification.path);
      if (!existsSync(target.fullPath)) {
        errorCode = "ASSERTION_TARGET_MISSING";
      } else if (pathContainsReparsePoint(task.workspace, target.fullPath)) {
        errorCode = "ASSERTION_TARGET_REPARSE";
      } else {
        const targetStat = lstatSync(target.fullPath);
        if (!targetStat.isFile()) {
          errorCode = "ASSERTION_TARGET_NOT_REGULAR_FILE";
        } else {
          const canonicalTarget = realpathSync.native(target.fullPath);
          if (!isWithin(canonicalWorkspace, canonicalTarget)) {
            errorCode = "ASSERTION_TARGET_OUTSIDE_WORKSPACE";
          } else {
            const bytes = readFileSync(target.fullPath);
            actualByteLength = bytes.length;
            actualSha256 = sha256(bytes);
            if (
              actualByteLength !== verification.byte_length ||
              actualSha256 !== verification.sha256
            ) {
              errorCode = "FILE_BYTES_MISMATCH";
            }
          }
        }
      }
    } catch {
      errorCode = "ASSERTION_READ_ERROR";
    }
    const receipt = Object.freeze({
      kind: "FILE_BYTES",
      phase: "HOST_POST_WRITE",
      path: verification.path,
      expected_sha256: verification.sha256,
      expected_byte_length: verification.byte_length,
      actual_sha256: actualSha256,
      actual_byte_length: actualByteLength,
      passed: errorCode === null,
      error_code: errorCode,
    });
    receipts.push(receipt);
    if (errorCode) errors.push(errorCode);
  }

  return Object.freeze({
    passed: errors.length === 0,
    errorCodes: Object.freeze([...new Set(errors)]),
    changedPaths: Object.freeze(changedTargets),
    commandsRun: Object.freeze(commandsRun),
    receipts: Object.freeze(receipts),
    tests: Object.freeze(receipts.map((receipt) =>
      receipt.kind === "COMMAND" ? commandReceiptTest(receipt) : fileReceiptTest(receipt),
    )),
  });
}

async function applyHostWriteVerification(
  handoff,
  task,
  {
    changedPaths = [],
    commandRunner = runApprovedCommand,
    signal,
    stagedApplicationReceipts = [],
  } = {},
) {
  if (
    task.mode !== "WRITE" ||
    handoff.status !== "PASS" ||
    handoff.execution_status !== "ACCEPTED"
  ) {
    return handoff;
  }
  const verification = await verifyWriteCompletion(task, {
    changedPaths,
    commandRunner,
    signal,
    stagedApplicationReceipts,
  });
  const authoritative = {
    ...handoff,
    commands_run: [...verification.commandsRun],
    tests: [...verification.tests],
    write_verification_receipts: [...verification.receipts],
  };
  if (verification.passed) return authoritative;
  return {
    ...authoritative,
    status: "FAIL",
    execution_status: "CONTRACT_ERROR",
    evidence_verdict: "UNRESOLVED",
    error_code: WRITE_VERIFICATION_FAILED,
    summary:
      `Host-side WRITE verification failed: ${verification.errorCodes.join(", ")}.`,
    positive_findings: [],
    residual_risks: [
      ...new Set([
        ...safeArray(handoff.residual_risks),
        "The attempted WRITE is not accepted until every host verifier passes.",
      ]),
    ],
    recommended_next_action:
      "Inspect the host verification receipts, correct the WRITE contract, and return to Sol.",
  };
}

function emptyUsage() {
  return {
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    prompt_cache_hit_tokens: 0,
    prompt_cache_miss_tokens: 0,
  };
}

function addUsage(total, usage = {}) {
  const promptTokens = Number(usage.prompt_tokens) || 0;
  const nestedCachedTokens = Number(usage.prompt_tokens_details?.cached_tokens) || 0;
  const cacheHitTokens = usage.prompt_cache_hit_tokens == null
    ? nestedCachedTokens
    : Number(usage.prompt_cache_hit_tokens) || 0;
  const cacheMissTokens = usage.prompt_cache_miss_tokens == null
    ? Math.max(0, promptTokens - cacheHitTokens)
    : Number(usage.prompt_cache_miss_tokens) || 0;
  const normalized = {
    prompt_tokens: promptTokens,
    completion_tokens: Number(usage.completion_tokens) || 0,
    total_tokens: Number(usage.total_tokens) || 0,
    prompt_cache_hit_tokens: cacheHitTokens,
    prompt_cache_miss_tokens: cacheMissTokens,
  };
  for (const key of Object.keys(total)) total[key] += normalized[key];
}

function safeUsageInteger(value, field) {
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value < 0
  ) {
    throw new Error(`provider usage ${field} must be a finite nonnegative safe integer`);
  }
  return value;
}

function strictProviderUsage(usage) {
  if (!usage || typeof usage !== "object" || Array.isArray(usage)) {
    throw new Error("provider usage is missing");
  }
  const promptTokens = safeUsageInteger(usage.prompt_tokens, "prompt_tokens");
  const completionTokens = safeUsageInteger(
    usage.completion_tokens,
    "completion_tokens",
  );
  const totalTokens = safeUsageInteger(usage.total_tokens, "total_tokens");
  if (totalTokens !== promptTokens + completionTokens) {
    throw new Error("provider usage total_tokens is inconsistent");
  }
  const explicitCached = usage.prompt_cache_hit_tokens;
  const nestedCached = usage.prompt_tokens_details?.cached_tokens;
  if (
    explicitCached != null &&
    nestedCached != null &&
    safeUsageInteger(explicitCached, "prompt_cache_hit_tokens") !==
      safeUsageInteger(nestedCached, "prompt_tokens_details.cached_tokens")
  ) {
    throw new Error("provider cached-token usage is inconsistent");
  }
  const cachedTokens = explicitCached != null
    ? safeUsageInteger(explicitCached, "prompt_cache_hit_tokens")
    : nestedCached != null
      ? safeUsageInteger(nestedCached, "prompt_tokens_details.cached_tokens")
      : 0;
  if (cachedTokens > promptTokens) {
    throw new Error("provider cached-token usage exceeds prompt_tokens");
  }
  const explicitUncached = usage.prompt_cache_miss_tokens;
  const uncachedTokens = explicitUncached == null
    ? promptTokens - cachedTokens
    : safeUsageInteger(explicitUncached, "prompt_cache_miss_tokens");
  if (cachedTokens + uncachedTokens !== promptTokens) {
    throw new Error("provider cached and uncached usage is inconsistent");
  }
  return Object.freeze({
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    total_tokens: totalTokens,
    prompt_cache_hit_tokens: cachedTokens,
    prompt_cache_miss_tokens: uncachedTokens,
  });
}

function nanoUsdCost(usage, rates = DEEPINFRA_V4_FLASH_NANO_USD) {
  const cost =
    BigInt(usage.prompt_cache_hit_tokens) * BigInt(rates.cached_input) +
    BigInt(usage.prompt_cache_miss_tokens) * BigInt(rates.uncached_input) +
    BigInt(usage.completion_tokens) * BigInt(rates.output);
  if (cost > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error("provider usage cost exceeds the safe integer bound");
  }
  return Number(cost);
}

function deepinfraTierRates(task) {
  if (task.primaryProfile === "deepinfra-fast") return DEEPINFRA_V4_FLASH_NANO_USD;
  if (task.primaryProfile === "deepinfra-normal") return DEEPINFRA_V4_FLASH_STANDARD_NANO_USD;
  if (task.primaryProfile === "deepinfra-flex") return DEEPINFRA_V4_FLASH_FLEX_NANO_USD;
  if (task.primaryProfile === "cheapluna-chat") return DEEPSEEK_V4_FLASH_NANO_USD;
  return null;
}

function deepinfraTierServiceTier(profile) {
  if (profile === "deepinfra-fast") return "priority";
  if (profile === "deepinfra-normal") return "standard";
  if (profile === "deepinfra-flex") return "flex";
  if (profile === "cheapluna-chat") return "standard";
  return undefined;
}

function isDeepInfraProfile(profile) {
  return profile === "deepinfra-fast" ||
    profile === "deepinfra-normal" ||
    profile === "deepinfra-flex";
}

function expectedFlashModel(profile) {
  if (profile === "cheapluna-chat") return "deepseek-v4-flash";
  return "deepseek-ai/DeepSeek-V4-Flash-0731";
}

function supportedProductionPriceTuple(task) {
  return deepinfraTierRates(task) !== null &&
    task?.model === expectedFlashModel(task?.primaryProfile) &&
    task?.serviceTier === deepinfraTierServiceTier(task?.primaryProfile) &&
    task?.reasoningEffort === "none";
}

function supportedFlashReasoningPriceTuple(task) {
  return deepinfraTierRates(task) !== null &&
    task?.model === expectedFlashModel(task?.primaryProfile) &&
    task?.serviceTier === deepinfraTierServiceTier(task?.primaryProfile) &&
    (task?.reasoningEffort === "high" || task?.reasoningEffort === "max");
}

function supportedV4ProPriceTuple(task) {
  return task?.primaryProfile === "deepinfra-fast" &&
    task?.model === "deepseek-ai/DeepSeek-V4-Pro" &&
    task?.serviceTier === "priority" &&
    task?.reasoningEffort === "none";
}

function supportedNemotronPriceTuple(task) {
  return task?.primaryProfile === "deepinfra-fast" &&
    task?.model === "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B" &&
    task?.serviceTier === "priority" &&
    task?.reasoningEffort === "high";
}

function supportedGlmPriceTuple(task) {
  return task?.primaryProfile === "deepinfra-fast" &&
    task?.model === GLM_FALLBACK.model &&
    task?.serviceTier === "priority" &&
    task?.reasoningEffort === GLM_FALLBACK.reasoning;
}

function priceTuple(task, budgetController) {
  const flash = supportedProductionPriceTuple(task);
  const flashReasoning = supportedFlashReasoningPriceTuple(task);
  const v4Pro = supportedV4ProPriceTuple(task);
  const nemotron = supportedNemotronPriceTuple(task);
  const glm = supportedGlmPriceTuple(task);
  if (
    !flash &&
    !flashReasoning &&
    !v4Pro &&
    !nemotron &&
    !glm &&
    budgetController?.testOnlyAllowUnsupportedTuple !== true
  ) {
    const error = new Error(
      "unsupported provider price tuple; accepted tuples are DeepInfra " +
        "DeepSeek-V4-Flash-0731:none, DeepSeek-V4-Flash-0731:high, " +
        "DeepSeek-V4-Pro:none, " +
        "NVIDIA-Nemotron-3-Ultra-550B-A55B:high, " +
        "GLM-5.2:high, " +
        "and DeepSeek deepseek-v4-flash (CheapLuna Chat):none|high",
    );
    Object.defineProperties(error, {
      code: { value: "UNSUPPORTED_PRICE_TUPLE", enumerable: true },
      executionStatus: { value: "BLOCKED", enumerable: true },
      deepseekFailureClass: { value: "LOCAL_CONTRACT" },
      providerStarted: { value: false },
    });
    throw error;
  }
  const flashTierRates = deepinfraTierRates(task);
  const flashPricingVersion = flash || flashReasoning
    ? task.primaryProfile === "cheapluna-chat"
      ? flashReasoning
        ? task.reasoningEffort === "max"
          ? DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION_MAX
          : DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION_HIGH
        : DEEPSEEK_CHAT_PRICE_ESTIMATOR_VERSION
      : task.primaryProfile === "deepinfra-fast"
        ? flashReasoning
          ? PRICE_ESTIMATOR_VERSION_PRIORITY_REASONING
          : PRICE_ESTIMATOR_VERSION
        : task.primaryProfile === "deepinfra-flex"
          ? flashReasoning
            ? PRICE_ESTIMATOR_VERSION_FLEX_REASONING
            : PRICE_ESTIMATOR_VERSION_FLEX
          : flashReasoning
            ? PRICE_ESTIMATOR_VERSION_STANDARD_REASONING
            : PRICE_ESTIMATOR_VERSION_STANDARD
    : null;
  return Object.freeze({
    profile: task.primaryProfile,
    model: task.model,
    serviceTier: task.serviceTier,
    reasoningEffort: task.reasoningEffort,
    pricingVersion: glm
      ? GLM_PRICE_ESTIMATOR_VERSION
      : nemotron
        ? NEMOTRON_PRICE_ESTIMATOR_VERSION
        : v4Pro
          ? V4_PRO_PRICE_ESTIMATOR_VERSION
          : flashPricingVersion,
    rates: glm
      ? DEEPINFRA_GLM_5_2_PRIORITY_NANO_USD
      : nemotron
        ? DEEPINFRA_NEMOTRON_3_ULTRA_PRIORITY_NANO_USD
        : v4Pro
          ? DEEPINFRA_V4_PRO_PRIORITY_NANO_USD
          : flashReasoning || flash
            ? (flashTierRates ?? DEEPINFRA_V4_FLASH_NANO_USD)
            : DEEPINFRA_V4_FLASH_NANO_USD,
  });
}

function requireBudgetController(budgetController) {
  if (
    !budgetController ||
    typeof budgetController.reserveNextCall !== "function" ||
    typeof budgetController.reconcile !== "function"
  ) {
    const error = new Error(
      "CUMULATIVE_BUDGET_CONTROLLER_UNAVAILABLE: provider transmission is blocked",
    );
    Object.defineProperties(error, {
      code: { value: "CUMULATIVE_BUDGET_CONTROLLER_UNAVAILABLE", enumerable: true },
      executionStatus: { value: "BLOCKED", enumerable: true },
      deepseekFailureClass: { value: "LOCAL_CONTRACT" },
      providerStarted: { value: false },
      cumulativeBudgetSafe: { value: false, enumerable: true },
    });
    throw error;
  }
  return budgetController;
}

function requireRouteBudgetController(budgetController, route) {
  const normalizedRoute = String(route ?? "").toUpperCase();
  if (budgetController?.testOnlyAllowUnsupportedRoutes === true) {
    return requireBudgetController(budgetController);
  }
  if (
    budgetController?.isDurableTransmissionController === true &&
    budgetController?.cumulativeBudgetSafe === true &&
    typeof budgetController?.reserveNextCall === "function" &&
    typeof budgetController?.reconcile === "function" &&
    typeof budgetController?.supportsRoute === "function" &&
    budgetController.supportsRoute(normalizedRoute) === true
  ) {
    return budgetController;
  }
  const error = new Error(
    `CUMULATIVE_BUDGET_CONTROLLER_UNAVAILABLE: ${normalizedRoute} has no accepted ` +
      "route-specific price estimator and remains blocked",
  );
  Object.defineProperties(error, {
    code: { value: "CUMULATIVE_BUDGET_CONTROLLER_UNAVAILABLE", enumerable: true },
    route: { value: normalizedRoute, enumerable: true },
    executionStatus: { value: "BLOCKED", enumerable: true },
    deepseekFailureClass: { value: "LOCAL_CONTRACT" },
    providerStarted: { value: false },
    lunaProviderStarted: { value: false },
    fallbackProviderStarted: { value: false },
    headProviderStarted: { value: false },
    cumulativeBudgetSafe: { value: false, enumerable: true },
  });
  throw error;
}

function maximumEstimatedNanoUsd(serializedBody, maximumOutputTokens, rates) {
  const bytes = Buffer.byteLength(serializedBody, "utf8");
  const proportionalMargin = Math.ceil(
    (bytes * CONSERVATIVE_INPUT_TOKEN_MARGIN_BASIS_POINTS) / 10_000,
  );
  if (
    bytes >
    Number.MAX_SAFE_INTEGER -
      proportionalMargin -
      CONSERVATIVE_INPUT_TOKEN_FIXED_MARGIN
  ) {
    throw new Error("estimated provider input token bound exceeds the safe integer range");
  }
  const maximumInputTokens =
    bytes + proportionalMargin + CONSERVATIVE_INPUT_TOKEN_FIXED_MARGIN;
  const cost =
    BigInt(maximumInputTokens) * BigInt(rates.uncached_input) +
    BigInt(maximumOutputTokens) * BigInt(rates.output);
  if (cost > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error("estimated provider cost exceeds the safe integer bound");
  }
  return Object.freeze({
    maximumInputTokens,
    estimatedNanoUsd: Number(cost),
  });
}

export const DEEPINFRA_MODEL_LIMITS = Object.freeze({
  "deepseek-ai/DeepSeek-V4-Flash-0731": Object.freeze({
    contextTokens: 1_048_576,
    providerMaximumOutputTokens: 16_384,
  }),
  "deepseek-ai/DeepSeek-V4-Pro": Object.freeze({
    contextTokens: 1_048_576,
    providerMaximumOutputTokens: 16_384,
  }),
  "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B": Object.freeze({
    contextTokens: 262_144,
    providerMaximumOutputTokens: 16_384,
  }),
  [GLM_FALLBACK.model]: Object.freeze({
    contextTokens: 1_048_576,
    providerMaximumOutputTokens: 16_384,
  }),
});

function assertProviderModelEnvelope(task, maximumInputTokens, maximumOutputTokens) {
  const limits = DEEPINFRA_MODEL_LIMITS[task?.model];
  if (!limits) return;
  const totalTokens = BigInt(maximumInputTokens) + BigInt(maximumOutputTokens);
  if (
    maximumOutputTokens > limits.providerMaximumOutputTokens ||
    totalTokens > BigInt(limits.contextTokens)
  ) {
    const error = new Error(
      `provider model token envelope exceeded: model=${task.model} ` +
        `input=${maximumInputTokens} output=${maximumOutputTokens} ` +
        `total=${totalTokens} context_limit=${limits.contextTokens} ` +
        `output_limit=${limits.providerMaximumOutputTokens}`,
    );
    Object.defineProperties(error, {
      code: { value: "MODEL_CONTEXT_LIMIT_EXCEEDED", enumerable: true },
      executionStatus: { value: "BLOCKED", enumerable: true },
      deepseekFailureClass: { value: "LOCAL_CONTRACT" },
      providerStarted: { value: false, enumerable: true },
    });
    throw error;
  }
}

function estimatedNanoUsdForTokenBound(
  maximumInputTokens,
  maximumOutputTokens,
  rates,
) {
  if (
    !Number.isSafeInteger(maximumInputTokens) ||
    maximumInputTokens < 0 ||
    !Number.isSafeInteger(maximumOutputTokens) ||
    maximumOutputTokens < 0
  ) {
    throw new Error("estimated provider token bound is invalid");
  }
  const cost =
    BigInt(maximumInputTokens) * BigInt(rates.uncached_input) +
    BigInt(maximumOutputTokens) * BigInt(rates.output);
  if (cost > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error("estimated provider cost exceeds the safe integer bound");
  }
  return Number(cost);
}

function accountingUncertainError(error, code = "ACCOUNTING_UNCERTAIN") {
  const normalized = error instanceof Error ? error : new Error(String(error));
  const wrapped = new Error(
    `${code}: ${safeDiagnosticText(normalized)}`,
    { cause: normalized },
  );
  Object.defineProperties(wrapped, {
    code: { value: code, enumerable: true },
    executionStatus: { value: "BLOCKED", enumerable: true },
    deepseekFailureClass: { value: "LOCAL_CONTRACT" },
    accountingUncertain: { value: true, enumerable: true },
  });
  return wrapped;
}

async function reconcileUnknown(budgetController, reservation) {
  try {
    await budgetController.reconcile(reservation, {
      outcome: "UNKNOWN",
      usage: null,
      actualNanoUsd: null,
      costPolicyVersion: COST_POLICY_VERSION,
      pricingVersion: reservation?.pricingVersion ?? PRICE_ESTIMATOR_VERSION,
    });
  } catch {
    // Best effort only: the caller still fails closed with ACCOUNTING_UNCERTAIN.
  }
}

async function reconcileUnknownStrict(budgetController, reservation) {
  try {
    await budgetController.reconcile(reservation, {
      outcome: "UNKNOWN",
      usage: null,
      actualNanoUsd: null,
      costPolicyVersion: COST_POLICY_VERSION,
      pricingVersion: reservation?.pricingVersion ?? PRICE_ESTIMATOR_VERSION,
    });
  } catch (error) {
    throw accountingUncertainError(error);
  }
}

function auditNegativeAdmissionPersistenceFailure(audit, error, context = {}) {
  try {
    audit({
      event: "negative_admission_persistence_failure",
      status: "BLOCKED",
      ...context,
      error: safeDiagnosticText(error),
    });
  } catch {
    // Diagnostics must never replace the typed provider or accounting outcome.
  }
}

function releaseNegativeAdmissionClaim(admissionClaim, audit, context = {}) {
  if (!admissionClaim?.release) return;
  try {
    admissionClaim.release();
  } catch (error) {
    auditNegativeAdmissionPersistenceFailure(audit, error, {
      stage: "release",
      ...context,
    });
  }
}

function attachRunMetrics(error, usage, apiCalls, observability = null) {
  const normalized = error instanceof Error ? error : new Error(String(error));
  const properties = {
    deepseekUsage: { value: { ...usage }, enumerable: false },
    deepseekApiCalls: { value: apiCalls, enumerable: false },
  };
  if (observability) {
    properties.deepseekObservability = {
      value: observability,
      enumerable: false,
    };
  }
  Object.defineProperties(normalized, properties);
  return normalized;
}

function safeArray(value) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

export function compactSolHandoff(handoff, { resultPath = null, maxWords = 300 } = {}) {
  const compact = {
    status: String(handoff?.status ?? "FAIL"),
    summary: truncateWords(handoff?.summary ?? "No summary supplied.", 60),
    evidence_path: resultPath,
    files_inspected: safeArray(handoff?.files_inspected).slice(0, 8),
    files_changed: safeArray(handoff?.files_changed).slice(0, 8),
    tests: safeArray(handoff?.tests)
      .slice(0, 5)
      .map((item) => truncateWords(item, 20)),
    positive_findings: safeArray(handoff?.positive_findings)
      .slice(0, 3)
      .map((item) => truncateWords(item, 20)),
    negative_findings: safeArray(handoff?.negative_findings)
      .slice(0, 3)
      .map((item) => truncateWords(item, 20)),
    gates: {
      scientific_uncertainty: Boolean(handoff?.scientific_uncertainty),
      architecture_uncertainty: Boolean(handoff?.architecture_uncertainty),
      scope_deviation: Boolean(handoff?.scope_deviation),
    },
    residual_risks: safeArray(handoff?.residual_risks)
      .slice(0, 3)
      .map((item) => truncateWords(item, 20)),
    recommended_next_action: truncateWords(handoff?.recommended_next_action ?? "Return to Sol", 40),
  };
  let serialized = JSON.stringify(compact);
  if (serialized.trim().split(/\s+/).length <= maxWords) return serialized;
  compact.summary = truncateWords(compact.summary, 25);
  compact.tests = compact.tests.slice(0, 2);
  compact.positive_findings = compact.positive_findings.slice(0, 1);
  compact.negative_findings = compact.negative_findings.slice(0, 1);
  compact.residual_risks = compact.residual_risks.slice(0, 1);
  compact.recommended_next_action = truncateWords(compact.recommended_next_action, 20);
  serialized = JSON.stringify(compact);
  return serialized;
}

function normalizeHandoff(handoff, task, runtime) {
  if (!handoff || !LEGACY_HANDOFF_KEYS.every((key) => Object.hasOwn(handoff, key))) {
    throw new Error("worker did not return the required structured handoff");
  }
  const normalizedSemantics = normalizeResult({
    status: String(handoff.status ?? "").toUpperCase(),
    execution_status: handoff.execution_status
      ? String(handoff.execution_status).toUpperCase()
      : undefined,
    evidence_verdict: handoff.evidence_verdict
      ? String(handoff.evidence_verdict).toUpperCase()
      : undefined,
  });
  const workerCitations = Array.isArray(handoff.citations) ? handoff.citations : [];
  const requiresEvidence = (task.requiredReads ?? []).length > 0;
  const result = {
    status: legacyStatus(normalizedSemantics),
    execution_status: normalizedSemantics.execution_status,
    evidence_verdict: normalizedSemantics.evidence_verdict,
    coverage_status: requiresEvidence ? "PENDING" : "NOT_REQUESTED",
    summary: String(handoff.summary ?? "").trim(),
    files_inspected: requiresEvidence
      ? []
      : [...new Set([...safeArray(handoff.files_inspected), ...runtime.inspectedPaths])],
    files_changed: [...runtime.changedPaths],
    commands_run: [...runtime.commandsRun],
    tests: safeArray(handoff.tests),
    positive_findings: safeArray(handoff.positive_findings),
    negative_findings: safeArray(handoff.negative_findings),
    scientific_uncertainty: Boolean(handoff.scientific_uncertainty),
    architecture_uncertainty: Boolean(handoff.architecture_uncertainty),
    scope_deviation: Boolean(handoff.scope_deviation),
    residual_risks: safeArray(handoff.residual_risks),
    recommended_next_action: String(handoff.recommended_next_action ?? "Return to Sol"),
  };
  if (!result.summary) {
    result.status = "FAIL";
    result.execution_status = "INCOMPLETE";
    result.evidence_verdict = "UNRESOLVED";
    result.summary = "DeepSeek returned an empty summary.";
  }
  if (task.mode === "READ_ONLY" && result.files_changed.length > 0) result.scope_deviation = true;
  const mechanicalWritePendingSol =
    task.mode === "WRITE" &&
    result.evidence_verdict === "NOT_APPLICABLE";
  if (
    result.status === "PASS" &&
    (
      (result.scientific_uncertainty && !mechanicalWritePendingSol) ||
      result.architecture_uncertainty ||
      result.scope_deviation
    )
  ) {
    result.status = "BLOCKED";
    result.execution_status = "BLOCKED";
    result.evidence_verdict = "UNRESOLVED";
  }
  if (requiresEvidence) {
    const evidenceState = runtime.evidenceState();
    const validation = validateEvidenceResult({
      handoff: { ...result, citations: workerCitations },
      manifest: evidenceState.manifest,
      receipts: evidenceState.receipts,
      requiredReads: task.requiredReads,
      coverageSpec: evidenceState.coverageSpec,
      jobId: task.jobId,
      workspaceInstanceId: task.workspaceInstanceId,
      resolvePath: (relative) => path.resolve(task.workspace, relative),
    });
    result.coverage_status = validation.coverage_status;
    result.execution_status = validation.execution_status;
    result.evidence_verdict = validation.evidence_verdict;
    result.status = legacyStatus(normalizeResult({
      execution_status: result.execution_status,
      evidence_verdict: result.evidence_verdict,
    }));
    result.files_inspected = [...validation.files_inspected];
    result.citations = [...validation.citations];
    result.evidence_errors = [...validation.errors];
    result.evidence_receipts = [...evidenceState.receipts];
  }
  return result;
}

export function classifyDeepSeekFailure(
  task,
  { handoff = null, error = null, timedOut = false, cancelled = false } = {},
) {
  if (cancelled) return "STOP_FOR_SOL";
  if (error?.accountingUncertain === true || error?.code === "ACCOUNTING_UNCERTAIN") {
    return "STOP_FOR_SOL";
  }
  if (
    handoff?.execution_status === "CONTRACT_ERROR" ||
    isDeterministicRequestRejection(error)
  ) return "DETERMINISTIC_REQUEST_REJECTED";
  if (error?.deepseekFailureClass === "LOCAL_CONTRACT") return "STOP_FOR_SOL";
  if (
    handoff?.scientific_uncertainty ||
    handoff?.architecture_uncertainty ||
    handoff?.scope_deviation ||
    handoff?.status === "BLOCKED"
  ) {
    return "STOP_FOR_SOL";
  }
  if (task.mode === "READ_ONLY" && (timedOut || error?.deepseekFailureClass === "TRANSIENT")) {
    return "TRANSIENT_READ_ONLY";
  }
  if (handoff?.status === "PASS") return "SUCCESS";
  if (
    error?.deepseekFailureClass === "TRANSIENT" ||
    error?.deepseekFailureClass === "PROVIDER_UNAVAILABLE"
  ) {
    return "NONRETRYABLE_PROVIDER";
  }
  return "NONRETRYABLE_TASK";
}

function apiFailure(status, label = "Primary provider API") {
  const messages = {
    400: `${label} rejected the request format (400)`,
    401: `${label} authentication failed (401)`,
    402: `${label} balance is insufficient (402)`,
    422: `${label} rejected request parameters (422)`,
    429: `${label} rate limit was reached (429)`,
    500: `${label} encountered a server error (500)`,
    503: `${label} is overloaded (503)`,
  };
  const error = new Error(messages[status] ?? `${label} request failed (${status})`);
  const deterministic = isDeterministicRequestRejection({ status });
  Object.defineProperties(error, {
    httpStatus: { value: status, enumerable: true },
    executionStatus: {
      value: deterministic ? "CONTRACT_ERROR" : "PROVIDER_ERROR",
      enumerable: true,
    },
    negativeAdmissionEligible: { value: deterministic, enumerable: true },
    deepseekFailureClass: {
      value: deterministic
        ? "DETERMINISTIC_REQUEST_REJECTED"
        : new Set([429, 500, 503]).has(status)
          ? "TRANSIENT"
          : new Set([401, 402]).has(status)
            ? "PROVIDER_UNAVAILABLE"
            : "MODEL_CONTRACT",
      enumerable: false,
    },
  });
  return error;
}

function assistantTranscript(task, message) {
  const transcript = {
    role: "assistant",
    content: message.content ?? null,
  };
  if (message.reasoning_content != null) {
    transcript.reasoning_content = message.reasoning_content;
  }
  if (Array.isArray(message.tool_calls) && message.tool_calls.length > 0) {
    transcript.tool_calls = message.tool_calls.map((call) => ({
      id: call.id,
      type: "function",
      function: {
        name: call?.function?.name,
        arguments: call?.function?.arguments,
      },
    }));
  }
  return transcript;
}

function negativeAdmissionError(record) {
  const semantics = contractErrorSemantics({
    summary: "The exact request matches a bounded deterministic negative admission.",
    code: "NEGATIVE_ADMISSION",
    httpStatus: record.http_status,
    negativeAdmission: true,
  });
  const error = new Error(semantics.summary);
  Object.defineProperties(error, {
    code: { value: semantics.error_code, enumerable: true },
    executionStatus: { value: semantics.execution_status, enumerable: true },
    httpStatus: { value: semantics.http_status, enumerable: true },
    negativeAdmissionEligible: { value: true, enumerable: true },
    negativeAdmissionHit: { value: true, enumerable: true },
    deepseekFailureClass: {
      value: "DETERMINISTIC_REQUEST_REJECTED",
      enumerable: false,
    },
  });
  return error;
}

function providerCallCapError(maximumProviderCalls, completedProviderCalls) {
  const error = new Error(
    `${MAXIMUM_PROVIDER_CALLS_EXHAUSTED}: maximum_provider_calls=` +
      `${maximumProviderCalls} permits no additional provider request`,
  );
  Object.defineProperties(error, {
    code: { value: MAXIMUM_PROVIDER_CALLS_EXHAUSTED, enumerable: true },
    executionStatus: { value: "BLOCKED", enumerable: true },
    deepseekFailureClass: { value: "LOCAL_CONTRACT" },
    providerStarted: { value: completedProviderCalls > 0, enumerable: true },
    maximumProviderCalls: { value: maximumProviderCalls, enumerable: true },
    completedProviderCalls: { value: completedProviderCalls, enumerable: true },
  });
  return error;
}

function canonicalProviderToolRequest(call) {
  const name = String(call?.function?.name ?? "");
  const rawArguments = String(call?.function?.arguments ?? "{}");
  let args;
  try {
    args = JSON.parse(rawArguments);
  } catch {
    args = { invalid_json_sha256: sha256(rawArguments) };
  }
  return Object.freeze({ name, arguments: args });
}

export function providerProgressFingerprint(message) {
  const toolRequests = (Array.isArray(message?.tool_calls) ? message.tool_calls : [])
    .map(canonicalProviderToolRequest)
    .sort((left, right) => canonicalHash(left).localeCompare(canonicalHash(right)));
  let governed = null;
  if (typeof message?.content === "string" && message.content.trim()) {
    try {
      const parsed = JSON.parse(message.content);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        governed = {
          status: parsed.status ?? null,
          execution_status: parsed.execution_status ?? null,
          evidence_verdict: parsed.evidence_verdict ?? null,
          positive_findings: Array.isArray(parsed.positive_findings)
            ? parsed.positive_findings
            : [],
          negative_findings: Array.isArray(parsed.negative_findings)
            ? parsed.negative_findings
            : [],
        };
      }
    } catch {
      governed = null;
    }
  }
  return canonicalHash({ governed, tool_requests: toolRequests });
}

export function hasDegenerateRepeatedSpan(content) {
  if (typeof content !== "string") return false;
  const normalized = content.toLowerCase().replace(/\s+/g, " ").trim();
  if (normalized.length < 512) return false;
  const tokens = normalized.split(" ");
  const windowSize = 32;
  if (tokens.length < windowSize * 4) return false;
  const windows = new Map();
  for (let index = 0; index <= tokens.length - windowSize; index += 1) {
    const signature = tokens.slice(index, index + windowSize).join(" ");
    const previous = windows.get(signature);
    if (!previous) {
      windows.set(signature, { count: 1, lastIndex: index });
      continue;
    }
    if (index - previous.lastIndex < windowSize) continue;
    previous.count += 1;
    previous.lastIndex = index;
    if (previous.count >= 4) return true;
  }
  return false;
}

function asksRepeatedClarification(content) {
  if (typeof content !== "string") return false;
  const normalized = content.toLowerCase().replace(/\s+/g, " ").trim();
  return /\b(?:did|do|have)\s+i\s+(?:understand|understood|get)\b/.test(normalized) ||
    /\bplease\s+confirm\b/.test(normalized) ||
    /\bcan\s+you\s+confirm\b/.test(normalized) ||
    /\bis\s+that\s+correct\b/.test(normalized);
}

function providerLoopGuardError(code, message) {
  const error = new Error(`${code}: ${message}`);
  Object.defineProperties(error, {
    code: { value: code, enumerable: true },
    executionStatus: { value: "BLOCKED", enumerable: true },
    deepseekFailureClass: { value: "LOCAL_CONTRACT" },
    automaticRetry: { value: false, enumerable: true },
  });
  return error;
}

export async function runDeepSeekAgent(
  task,
  {
    apiKey = resolvePrimaryApiKey(resolvePrimaryProfile(task.primaryProfile)),
    fetchFunction = globalThis.fetch,
    budgetController = null,
    negativeAdmissionCoordinator = null,
    signal,
    commandRunner,
    evidenceContext = null,
    audit = () => {},
  } = {},
) {
  if (task?.localExactWrite === true) {
    const error = new Error(
      "LOCAL exact-byte WRITE cannot be transmitted to a provider",
    );
    Object.defineProperties(error, {
      executionStatus: { value: "BLOCKED", enumerable: true },
      deepseekFailureClass: { value: "LOCAL_CONTRACT" },
      providerStarted: { value: false },
    });
    throw error;
  }
  const controller = requireBudgetController(budgetController);
  if (!String(apiKey ?? "").trim()) throw new Error(`${task.credentialEnv} is not configured`);
  if (typeof fetchFunction !== "function") throw new Error("direct HTTP fetch is unavailable");
  const pricing = priceTuple(task, controller);
  const runtime = createRepositoryTools(task, { commandRunner, signal, evidenceContext });
  const usage = emptyUsage();
  let apiCalls = 0;
  let observedServiceTier = null;
  const flashPackedWrite = task.packedEvidenceMode === FLASH_PACKED_WRITE_MODE;
  const flashPacked = new Set([
    FLASH_PACKED_EVIDENCE_MODE,
    FLASH_PACKED_WRITE_MODE,
  ]).has(task.packedEvidenceMode);
  let flashPackedStage = flashPacked ? "evidence_pack" : null;
  let flashPackedPack = null;
  let flashPackedBuilt = null;
  let flashPackedPreflight = null;
  let flashPackedRequestContext = null;
  let flashPackedReservation = null;
  let flashPackedUsage = null;
  let flashPackedActualNanoUsd = null;
  let flashPackedReconciliationState = null;
  let flashPackedObservability = null;
  const seenProgressFingerprints = new Set();
  const seenToolRequestHashes = new Set();
  const maximumProviderCalls =
    task.routeConstraints?.maximumProviderCalls ?? DEFAULT_ROUTE_LIMITS.maximumProviderCalls;
  if (
    !Number.isSafeInteger(maximumProviderCalls) ||
    maximumProviderCalls < 1 ||
    maximumProviderCalls > MAX_TOOL_TURNS
  ) {
    throw new Error(
      `normalized maximumProviderCalls must be a safe integer between 1 and ${MAX_TOOL_TURNS}`,
    );
  }

  try {
    let messages;
    if (flashPacked) {
      flashPackedPack = runtime.packRequiredEvidence();
      flashPackedStage = "pack_size";
      flashPackedBuilt = buildFlashPackedMessages(task, flashPackedPack);
      messages = [...flashPackedBuilt.messages];
    } else {
      const prompt = buildWorkerPrompt(task);
      messages = [
        { role: "system", content: prompt.system },
        { role: "user", content: prompt.user },
      ];
    }
    for (let turn = 1; turn <= MAX_TOOL_TURNS; turn += 1) {
      if (apiCalls >= maximumProviderCalls) {
        throw providerCallCapError(maximumProviderCalls, apiCalls);
      }
      const forceFinal =
        apiCalls + 1 === maximumProviderCalls || turn === MAX_TOOL_TURNS;
      if (forceFinal && !flashPacked) {
        messages.push({
          role: "user",
          content: [
            "The tool budget is exhausted. Do not call any more tools.",
            "Return the required structured handoff JSON now, using only evidence already collected.",
            `Required keys: ${HANDOFF_KEYS.join(", ")}.`,
            `JSON example: ${JSON.stringify({
              status: "PASS",
              execution_status: "ACCEPTED",
              evidence_verdict: "NOT_APPLICABLE",
              summary: "bounded work completed",
              files_inspected: [],
              files_changed: [],
              commands_run: [],
              tests: [],
              positive_findings: [],
              negative_findings: [],
              citations: [],
              scientific_uncertainty: false,
              architecture_uncertainty: false,
              scope_deviation: false,
              residual_risks: [],
              recommended_next_action: "Return to Sol",
            })}`,
          ].join("\n"),
        });
      }
      const canonicalRequest = buildDeepSeekRequest(
        task,
        messages,
        flashPacked ? [] : runtime.definitions,
        { forceFinal, packedEvidence: flashPacked ? flashPackedPack : null },
      );
      const serializedBody = JSON.stringify(canonicalRequest);
      const requestIdentityHash = sha256(serializedBody);
      let estimate = maximumEstimatedNanoUsd(
        serializedBody,
        task.maxOutputTokens,
        pricing.rates,
      );
      if (flashPacked) {
        const requestBodyBytes = Buffer.byteLength(serializedBody, "utf8");
        const stablePrefix = flashPackedStablePrefixIdentity(serializedBody, messages);
        flashPackedStage = "transport_gate";
        if (requestBodyBytes > MAX_FLASH_PACKED_REQUEST_BODY_BYTES) {
          flashPackedPreflight = Object.freeze({
            prompt_chars: flashPackedBuilt.promptChars,
            prompt_char_limit: MAX_GLM_PACKED_PROMPT_CHARS,
            request_body_bytes: requestBodyBytes,
            transport_body_limit_bytes: MAX_FLASH_PACKED_REQUEST_BODY_BYTES,
            transport_body_within_limit: false,
          });
          throw new Error(
            `Flash packed request body ${requestBodyBytes} bytes exceeds transport ceiling ` +
              `${MAX_FLASH_PACKED_REQUEST_BODY_BYTES}`,
          );
        }
        flashPackedStage = "tokenizer_identity";
        const tokenizerEstimate = estimateDeepSeekV4FlashPrompt(
          canonicalRequest,
          serializedBody,
        );
        estimate = Object.freeze({
          maximumInputTokens: tokenizerEstimate.estimated_input_tokens,
          estimatedNanoUsd: estimatedNanoUsdForTokenBound(
            tokenizerEstimate.estimated_input_tokens,
            task.maxOutputTokens,
            pricing.rates,
          ),
          tokenizer: tokenizerEstimate,
        });
        const estimatedCostUsd = estimate.estimatedNanoUsd / 1_000_000_000;
        flashPackedPreflight = Object.freeze({
          prompt_chars: flashPackedBuilt.promptChars,
          prompt_char_limit: MAX_GLM_PACKED_PROMPT_CHARS,
          request_body_bytes: requestBodyBytes,
          transport_body_limit_bytes: MAX_FLASH_PACKED_REQUEST_BODY_BYTES,
          transport_body_within_limit: true,
          tokenizer_status: tokenizerEstimate.tokenizer_status,
          tokenizer_failure_reason:
            tokenizerEstimate.tokenizer_failure_reason,
          tokenizer_model: tokenizerEstimate.model,
          tokenizer_revision: tokenizerEstimate.revision,
          tokenizer_package: tokenizerEstimate.package,
          tokenizer_package_version: tokenizerEstimate.package_version,
          tokenizer_artifact_sha256:
            tokenizerEstimate.tokenizer_artifact_sha256,
          tokenizer_config_sha256:
            tokenizerEstimate.tokenizer_config_sha256,
          tokenizer_encoding_sha256:
            tokenizerEstimate.encoding_artifact_sha256,
          tokenized_prompt_tokens:
            tokenizerEstimate.tokenized_prompt_tokens,
          constraint_schema_tokens:
            tokenizerEstimate.constraint_schema_tokens,
          tokenizer_margin_basis_points:
            tokenizerEstimate.tokenizer_margin_basis_points,
          tokenizer_margin_fixed_tokens:
            tokenizerEstimate.tokenizer_margin_fixed_tokens,
          tokenizer_margin_tokens:
            tokenizerEstimate.tokenizer_margin_tokens,
          estimated_input_tokens: estimate.maximumInputTokens,
          maximum_output_tokens: task.maxOutputTokens,
          estimated_total_tokens:
            estimate.maximumInputTokens + task.maxOutputTokens,
          estimated_cost_nano_usd: estimate.estimatedNanoUsd,
          estimated_cost_usd: estimatedCostUsd,
          cache_discount_assumed: false,
          service_tier: task.serviceTier,
          pricing_version: pricing.pricingVersion,
          stable_prefix_hash: stablePrefix.stablePrefixHash,
          stable_prefix_bytes: stablePrefix.stablePrefixBytes,
          prompt_schema_version: FLASH_PACKED_PROMPT_SCHEMA_VERSION,
        });
        flashPackedRequestContext = Object.freeze({
          requestIdentityHash,
          stablePrefix,
          requestBodyBytes,
          estimate,
        });
        if (tokenizerEstimate.tokenizer_status !== "VERIFIED") {
          throw new Error(
            "Flash packed tokenizer identity is unavailable; conservative fallback " +
              `${estimate.maximumInputTokens} tokens remains fail closed`,
          );
        }
        flashPackedStage = "cost_gate";
        if (estimate.maximumInputTokens > task.routeConstraints.maximumInputTokens) {
          throw new Error(
            `Flash packed evidence estimated input ${estimate.maximumInputTokens} tokens ` +
              `exceeds contract ceiling ${task.routeConstraints.maximumInputTokens}`,
          );
        }
        if (
          task.maxOutputTokens >
          task.routeConstraints.maximumOutputTokensTotal
        ) {
          throw new Error(
            `Flash packed evidence maximum output ${task.maxOutputTokens} tokens ` +
              `exceeds aggregate contract ceiling ` +
              `${task.routeConstraints.maximumOutputTokensTotal}`,
          );
        }
        if (
          BigInt(estimate.maximumInputTokens) + BigInt(task.maxOutputTokens) >
          BigInt(task.routeConstraints.maximumTotalTokens)
        ) {
          throw new Error(
            "Flash packed evidence estimated total tokens exceed the contract ceiling",
          );
        }
        if (estimatedCostUsd > task.routeConstraints.maximumEstimatedCostUsd) {
          throw new Error(
            `Flash packed evidence estimated cost ${estimatedCostUsd.toFixed(6)} USD ` +
              `exceeds contract ceiling ` +
              `${task.routeConstraints.maximumEstimatedCostUsd.toFixed(6)} USD`,
          );
        }
        audit({
          event: "flash_packed_evidence_preflight",
          status: "READY",
          stage: flashPackedStage,
          manifest_hash: flashPackedPack.manifest_hash,
          pack_hash: flashPackedPack.pack_hash,
          section_count: flashPackedPack.sections.length,
          ...flashPackedPreflight,
        });
        flashPackedStage = "cost_reservation";
      }
      assertProviderModelEnvelope(
        task,
        estimate.maximumInputTokens,
        task.maxOutputTokens,
      );
      let admissionClaim = null;
      if (negativeAdmissionCoordinator) {
        admissionClaim = await negativeAdmissionCoordinator.claim({
          projectId: task.projectId,
          requestIdentityHash,
          model: task.model,
          tier: task.tier,
          reasoning: task.reasoningEffort,
          workerPolicyVersion: WORKER_POLICY_VERSION,
        });
        if (admissionClaim.kind === "ADMITTED") {
          throw negativeAdmissionError(admissionClaim.record);
        }
      }
      let reservation;
      try {
        if (apiCalls >= maximumProviderCalls) {
          throw providerCallCapError(maximumProviderCalls, apiCalls);
        }
        reservation = await controller.reserveNextCall({
          task,
          projectId: task.projectId ?? "UNSCOPED",
          jobId: task.jobId ?? task.taskId ?? "UNASSIGNED",
          attemptId: task.attemptId ?? "UNASSIGNED",
          turn,
          requestIdentityHash,
          canonicalRequest,
          messages,
          maximumOutputTokens: task.maxOutputTokens,
          maximumInputTokens: estimate.maximumInputTokens,
          estimatedNanoUsd: estimate.estimatedNanoUsd,
          pricing,
          costPolicyVersion: COST_POLICY_VERSION,
        });
      } catch (error) {
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        throw error;
      }
      if (flashPacked) flashPackedReservation = reservation;
      if (signal?.aborted) {
        try {
          const released = await controller.reconcile(reservation, {
            outcome: "RELEASED",
            usage: null,
            actualNanoUsd: 0,
            costPolicyVersion: COST_POLICY_VERSION,
            pricingVersion: pricing.pricingVersion,
          });
          if (flashPacked) {
            flashPackedReconciliationState = released?.state ?? "RELEASED";
          }
        } catch (error) {
          await reconcileUnknown(controller, reservation);
          if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
          releaseNegativeAdmissionClaim(admissionClaim, audit, {
            request_identity_hash: requestIdentityHash,
          });
          throw accountingUncertainError(error);
        }
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        const aborted = new Error("provider request was cancelled before transmission");
        aborted.name = "AbortError";
        Object.defineProperties(aborted, {
          executionStatus: { value: "CANCELLED", enumerable: true },
          deepseekFailureClass: { value: "LOCAL_CONTRACT" },
          providerStarted: { value: false },
        });
        throw aborted;
      }
      let response;
      // REV-9 retry policy (CHEAPLUNA_RETRY_POLICY.json): 429 -> up to 2 retries
      // exponential backoff + jitter; 500 -> 1; 503 -> 2; 400/422 -> 0. A transient
      // HTTP failure is retried inside the provider loop so the run can still reach
      // an accepted handoff instead of failing the whole job. Each retry consumes a
      // provider-call slot (apiCalls) and re-reserves budget, so maximum_provider_calls
      // bounds the total attempts. flashPacked one-shot runs keep their single call.
      const transientRetries = (status) =>
        flashPacked || !Number.isInteger(status)
          ? 0
          : status === 429
            ? 2
            : status === 503
              ? 2
              : status === 500
                ? 1
                : 0;
      let retryCounter = 0;
      let transientStatus = null;
      for (;;) {
        try {
          if (flashPacked) flashPackedStage = "provider_request";
          apiCalls += 1;
          response = await fetchFunction(task.apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${apiKey}`,
          },
          body: serializedBody,
          signal,
        });
      } catch (error) {
        await reconcileUnknown(controller, reservation);
        if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        if (error?.name === "AbortError") {
          throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_AFTER_ABORT");
        }
        const networkError = new Error(
          `${task.primaryDisplayName} API network failure: ${safeDiagnosticText(error, [apiKey])}`,
        );
        Object.defineProperty(networkError, "deepseekFailureClass", {
          value: "TRANSIENT",
          enumerable: false,
        });
        throw accountingUncertainError(networkError, "ACCOUNTING_UNKNOWN_AFTER_FETCH");
      }
      if (!response.ok) {
        if (flashPacked) flashPackedStage = "provider_response";
        const failure = apiFailure(response.status, `${task.primaryDisplayName} API`);
        const allowedRetries = transientRetries(response.status);
        if (
          allowedRetries > 0 &&
          retryCounter < allowedRetries &&
          apiCalls < maximumProviderCalls
        ) {
          // Transient HTTP failure: back off exponentially with jitter and retry the
          // same request. The reservation and admission claim stay OPEN across retries
          // because each retry is the same logical provider transmission (identical
          // transmissionId); the transmission is reconciled exactly once at the end.
          transientStatus = response.status;
          retryCounter += 1;
          const baseDelayMs = 400 * 2 ** (retryCounter - 1);
          const jitterMs = Math.floor(Math.random() * baseDelayMs);
          await asyncDelay(baseDelayMs + jitterMs);
          continue;
        }
        if (isDeterministicRequestRejection(failure)) {
          try {
            const released = await controller.reconcile(reservation, {
              outcome: "RELEASED",
              usage: null,
              actualNanoUsd: 0,
              costPolicyVersion: COST_POLICY_VERSION,
              pricingVersion: pricing.pricingVersion,
            });
            if (flashPacked) {
              flashPackedReconciliationState = released?.state ?? "RELEASED";
            }
          } catch (error) {
            await reconcileUnknown(controller, reservation);
            if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
            releaseNegativeAdmissionClaim(admissionClaim, audit, {
              request_identity_hash: requestIdentityHash,
              http_status: response.status,
            });
            throw accountingUncertainError(error);
          }
          try {
            await admissionClaim?.publish?.({
              httpStatus: response.status,
              rejectionClass: "DETERMINISTIC_REQUEST_REJECTED",
            });
          } catch (error) {
            auditNegativeAdmissionPersistenceFailure(audit, error, {
              stage: "publish",
              request_identity_hash: requestIdentityHash,
              http_status: response.status,
            });
          } finally {
            releaseNegativeAdmissionClaim(admissionClaim, audit, {
              request_identity_hash: requestIdentityHash,
              http_status: response.status,
            });
          }
          throw failure;
        }
        try {
          await reconcileUnknownStrict(controller, reservation);
          if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
        } finally {
          releaseNegativeAdmissionClaim(admissionClaim, audit, {
            request_identity_hash: requestIdentityHash,
            http_status: response.status,
          });
        }
        throw failure;
      }
        break;
      }
      let responseText;
      try {
        if (flashPacked) flashPackedStage = "provider_response";
        responseText = await response.text();
      } catch (error) {
        await reconcileUnknown(controller, reservation);
        if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_DURING_BODY_READ");
      }
      let payload;
      try {
        if (flashPacked) flashPackedStage = "response_parse";
        payload = JSON.parse(responseText.trim());
      } catch (error) {
        await reconcileUnknown(controller, reservation);
        if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_MALFORMED_2XX");
      }
      let normalizedUsage;
      let actualNanoUsd;
      try {
        normalizedUsage = strictProviderUsage(payload.usage);
        actualNanoUsd = nanoUsdCost(normalizedUsage, pricing.rates);
        if (flashPacked) {
          flashPackedUsage = normalizedUsage;
          flashPackedActualNanoUsd = actualNanoUsd;
        }
      } catch (error) {
        await reconcileUnknown(controller, reservation);
        if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_INVALID_USAGE");
      }
      try {
        if (flashPacked) flashPackedStage = "accounting_reconcile";
        const reconciled = await controller.reconcile(reservation, {
          outcome: "RECONCILED",
          usage: normalizedUsage,
          actualNanoUsd,
          costPolicyVersion: COST_POLICY_VERSION,
          pricingVersion: pricing.pricingVersion,
        });
        if (flashPacked) {
          flashPackedReconciliationState = reconciled?.state ?? "RECONCILED";
          if (flashPackedReconciliationState !== "RECONCILED") {
            throw new Error(
              "Flash packed accounting controller did not confirm RECONCILED state",
            );
          }
        }
      } catch (error) {
        await reconcileUnknown(controller, reservation);
        if (flashPacked) flashPackedReconciliationState = "UNKNOWN";
        releaseNegativeAdmissionClaim(admissionClaim, audit, {
          request_identity_hash: requestIdentityHash,
        });
        throw accountingUncertainError(error);
      }
      releaseNegativeAdmissionClaim(admissionClaim, audit, {
        request_identity_hash: requestIdentityHash,
      });
      if (typeof payload.service_tier === "string") observedServiceTier = payload.service_tier;
      const choice = payload?.choices?.[0];
      const message = choice?.message;
      if (!message || message.role !== "assistant") {
        throw new Error("DeepSeek API response did not contain an assistant message");
      }
      addUsage(usage, normalizedUsage);
      if (
        task.requestDialect === "deepinfra-openai" &&
        observedServiceTier !== null &&
        observedServiceTier !== task.serviceTier
      ) {
        const mismatch = new Error(
          `DeepInfra service tier mismatch: requested=${task.serviceTier} ` +
            `observed=${observedServiceTier}`,
        );
        Object.defineProperties(mismatch, {
          code: { value: "SERVICE_TIER_MISMATCH", enumerable: true },
          executionStatus: { value: "BLOCKED", enumerable: true },
          deepseekFailureClass: { value: "LOCAL_CONTRACT" },
          providerStarted: { value: true, enumerable: true },
        });
        throw mismatch;
      }
      const toolCalls = Array.isArray(message.tool_calls) ? message.tool_calls : [];
      audit({
        turn,
        response_id: payload.id ?? null,
        model: payload.model ?? task.model,
        finish_reason: choice.finish_reason ?? null,
        usage: payload.usage ?? {},
        service_tier: payload.service_tier ?? null,
        tool_names: toolCalls.map((call) => call?.function?.name ?? "unknown"),
        content_present: Boolean(message.content),
      });
      if (flashPacked) {
        const contentPreview =
          typeof message.content === "string"
            ? message.content.slice(0, 500)
            : null;
        audit({
          event: "flash_packed_evidence_response",
          status: "RECEIVED",
          stage: "provider_response",
          response_id: payload.id ?? null,
          model: payload.model ?? task.model,
          finish_reason: choice.finish_reason ?? null,
          usage: payload.usage ?? {},
          service_tier: payload.service_tier ?? null,
          content_bytes:
            typeof message.content === "string"
              ? Buffer.byteLength(message.content, "utf8")
              : null,
          content_preview: contentPreview,
        });
      }
      if (choice.finish_reason === "length") {
        const truncation = new Error(
          "Primary worker output was truncated (finish_reason=length); narrow the task or raise " +
            "max_output_tokens within the validated bound before resubmitting.",
        );
        Object.defineProperty(truncation, "deepseekFailureClass", {
          value: "LOCAL_CONTRACT",
          enumerable: false,
        });
        throw truncation;
      }
      if (hasDegenerateRepeatedSpan(message.content)) {
        throw providerLoopGuardError(
          "DEGENERATE_PROVIDER_OUTPUT",
          "provider output repeated a normalized span without new evidence",
        );
      }
      if (toolCalls.length === 0 && asksRepeatedClarification(message.content)) {
        throw providerLoopGuardError(
          "REPEATED_PROVIDER_QUESTION",
          "provider asked for confirmation instead of returning the terminal result",
        );
      }
      const progressFingerprint = providerProgressFingerprint(message);
      if (seenProgressFingerprints.has(progressFingerprint)) {
        throw providerLoopGuardError(
          "REPEATED_PROVIDER_PROGRESS",
          "provider repeated an identical normalized progress state",
        );
      }
      seenProgressFingerprints.add(progressFingerprint);
      for (const call of toolCalls) {
        if (call?.function?.name === "finish_handoff") continue;
        const requestHash = canonicalHash(canonicalProviderToolRequest(call));
        if (seenToolRequestHashes.has(requestHash)) {
          throw providerLoopGuardError(
            "REPEATED_PROVIDER_PROGRESS",
            "provider repeated an identical tool request",
          );
        }
        seenToolRequestHashes.add(requestHash);
      }
      messages.push(assistantTranscript(task, message));

      if (flashPacked && toolCalls.length > 0) {
        throw providerLoopGuardError(
          "FLASH_PACKED_TOOL_CALL_FORBIDDEN",
          "Flash packed evidence must return one tool-free JSON handoff",
        );
      }
      if (
        forceFinal &&
        toolCalls.some((call) => call?.function?.name !== "finish_handoff")
      ) {
        throw providerCallCapError(maximumProviderCalls, apiCalls);
      }
      if (toolCalls.length === 0) {
        if (flashPacked) flashPackedStage = "handoff_validation";
        const parsedCandidate = parseCandidate(message.content);
        const writePlan = flashPackedWrite
          ? runtime.materializePackedWritePlan(parsedCandidate)
          : null;
        const candidate = flashPackedWrite
          ? writePlan.handoff
          : runtime.materializePackedHandoff(parsedCandidate);
        if (flashPackedWrite) {
          flashPackedStage = "precommit_manifest_freshness";
          runtime.assertRequiredEvidenceFresh();
        }
        const normalized = normalizeHandoff(candidate, task, runtime);
        let stagedApplication = null;
        let rollbackSnapshot = null;
        if (
          flashPackedWrite &&
          normalized.status === "PASS" &&
          normalized.execution_status === "ACCEPTED"
        ) {
          flashPackedStage = "staged_write_application";
          rollbackSnapshot = captureFlashWriteRollbackSnapshot(task);
          stagedApplication = await applyFlashPackedWritePlan(
            task,
            writePlan.writeOperations,
            {
              commandRunner,
              signal,
              assertRequiredReadsFresh: runtime.assertRequiredEvidenceFresh,
            },
          );
          for (const changedPath of stagedApplication.changedPaths) {
            if (!runtime.changedPaths.includes(changedPath)) {
              runtime.changedPaths.push(changedPath);
            }
          }
          normalized.files_changed = [...runtime.changedPaths];
        } else if (flashPackedWrite && writePlan.writeOperations.length > 0) {
          throw new Error(
            "Flash packed WRITE operations require a PASS/ACCEPTED handoff",
          );
        }
        let verified = await applyHostWriteVerification(normalized, task, {
          changedPaths: runtime.changedPaths,
          commandRunner,
          signal,
          stagedApplicationReceipts:
            stagedApplication?.applicationReceipts ?? [],
        });
        if (
          flashPackedWrite &&
          rollbackSnapshot &&
          verified.status === "FAIL" &&
          verified.execution_status === "CONTRACT_ERROR" &&
          verified.error_code === WRITE_VERIFICATION_FAILED
        ) {
          restoreFlashWriteRollbackSnapshot(task, rollbackSnapshot);
          runtime.changedPaths.length = 0;
          verified = {
            ...verified,
            files_changed: [],
            summary:
              `${verified.summary} The host restored every staged target and immutable ` +
              "required read to its pre-transaction bytes.",
            residual_risks: [
              ...new Set([
                ...safeArray(verified.residual_risks),
                "Host verification failed; no WRITE from this transaction remains.",
              ]),
            ],
          };
        }
        if (flashPacked) {
          flashPackedObservability = buildFlashPackedObservability({
            task,
            requestIdentityHash: flashPackedRequestContext.requestIdentityHash,
            stablePrefix: flashPackedRequestContext.stablePrefix,
            requestBodyBytes: flashPackedRequestContext.requestBodyBytes,
            estimate: flashPackedRequestContext.estimate,
            reservation: flashPackedReservation,
            pricing,
            usage: flashPackedUsage,
            actualNanoUsd: flashPackedActualNanoUsd,
            reconciliationState: flashPackedReconciliationState,
            apiCalls,
            handoff: verified,
          });
          audit(flashPackedObservability);
          audit({
            event: "flash_packed_evidence_complete",
            status: verified.status,
            stage: flashPackedStage,
            coverage_status: verified.coverage_status,
            api_calls: apiCalls,
            manifest_hash: flashPackedPack.manifest_hash,
            pack_hash: flashPackedPack.pack_hash,
          });
        }
        return {
          handoff: redactDiagnostic(verified, [apiKey]),
          usage,
          api_calls: apiCalls,
          service_tier: observedServiceTier,
          ...(flashPacked
            ? {
                observability: flashPackedObservability,
                packed_evidence: {
                  mode: task.packedEvidenceMode,
                  manifest_hash: flashPackedPack.manifest_hash,
                  pack_hash: flashPackedPack.pack_hash,
                  section_count: flashPackedPack.sections.length,
                  ...flashPackedPreflight,
                },
              }
            : {}),
        };
      }

      let finalHandoff = null;
      for (const call of toolCalls) {
        const name = call?.function?.name;
        let args;
        try {
          args = JSON.parse(call?.function?.arguments ?? "{}");
        } catch {
          args = null;
        }
        if (name === "finish_handoff" && args) {
          finalHandoff = args;
          continue;
        }
        let toolResult;
        try {
          if (!args) throw new Error("tool arguments are not valid JSON");
          toolResult = await runtime.execute(name, args);
        } catch (error) {
          toolResult = { error: safeDiagnosticText(error, [apiKey]) };
        }
        messages.push({
          role: "tool",
          tool_call_id: call.id,
          content: boundedText(JSON.stringify(toolResult)),
        });
      }
      if (finalHandoff) {
        let normalizedHandoff;
        try {
          normalizedHandoff = normalizeHandoff(finalHandoff, task, runtime);
          normalizedHandoff = await applyHostWriteVerification(normalizedHandoff, task, {
            changedPaths: runtime.changedPaths,
            commandRunner,
            signal,
          });
        } catch (error) {
          if (Number(payload?.usage?.completion_tokens) >= task.maxOutputTokens) {
            const truncation = new Error(
              "Primary worker returned an incomplete finish_handoff at the output-token ceiling; " +
                "narrow the task before resubmitting.",
            );
            Object.defineProperty(truncation, "deepseekFailureClass", {
              value: "LOCAL_CONTRACT",
              enumerable: false,
            });
            throw truncation;
          }
          Object.defineProperty(error, "deepseekFailureClass", {
            value: "LOCAL_CONTRACT",
            enumerable: false,
          });
          throw error;
        }
        return {
          handoff: redactDiagnostic(normalizedHandoff, [apiKey]),
          usage,
          api_calls: apiCalls,
          service_tier: observedServiceTier,
        };
      }
    }
    throw providerCallCapError(maximumProviderCalls, apiCalls);
  } catch (error) {
    const normalized = error instanceof Error ? error : new Error(String(error));
    if (flashPacked) {
      if (/stale manifest/i.test(normalized.message)) {
        flashPackedStage = "manifest_freshness";
      }
      if (apiCalls === 0 && !normalized.deepseekFailureClass) {
        Object.defineProperty(normalized, "deepseekFailureClass", {
          value: "LOCAL_CONTRACT",
          enumerable: false,
        });
      }
      if (apiCalls === 0 && !Object.hasOwn(normalized, "providerStarted")) {
        Object.defineProperty(normalized, "providerStarted", {
          value: false,
          enumerable: true,
        });
      }
      audit({
        event: "flash_packed_evidence_failure",
        status: "BLOCKED",
        stage: flashPackedStage,
        provider_started: apiCalls > 0,
        api_calls: apiCalls,
        error: safeDiagnosticText(normalized, [apiKey]),
        ...(flashPackedPreflight ?? {}),
      });
      if (flashPackedRequestContext) {
        try {
          flashPackedObservability = buildFlashPackedObservability({
            task,
            requestIdentityHash: flashPackedRequestContext.requestIdentityHash,
            stablePrefix: flashPackedRequestContext.stablePrefix,
            requestBodyBytes: flashPackedRequestContext.requestBodyBytes,
            estimate: flashPackedRequestContext.estimate,
            reservation: flashPackedReservation,
            pricing,
            usage: flashPackedUsage,
            actualNanoUsd: flashPackedActualNanoUsd,
            reconciliationState:
              flashPackedReconciliationState ??
              (apiCalls > 0
                ? "UNKNOWN"
                : flashPackedReservation
                  ? "NOT_TRANSMITTED"
                  : "NOT_RESERVED"),
            apiCalls,
          });
          audit(flashPackedObservability);
        } catch (observabilityError) {
          audit({
            event: "flash_packed_observability_failure",
            status: "BLOCKED",
            stage: flashPackedStage,
            provider_started: apiCalls > 0,
            api_calls: apiCalls,
            error: safeDiagnosticText(observabilityError, [apiKey]),
          });
        }
      }
    }
    throw attachRunMetrics(
      normalized,
      usage,
      apiCalls,
      flashPackedObservability,
    );
  }
}

export function estimateGlmPackedCost(promptChars, maxOutputTokens) {
  const estimatedInputTokens = Math.ceil(
    Number(promptChars) / CONSERVATIVE_PROMPT_CHARS_PER_TOKEN,
  );
  const estimatedOutputTokens = Number(maxOutputTokens);
  if (
    !Number.isFinite(estimatedInputTokens) ||
    estimatedInputTokens < 0 ||
    !Number.isInteger(estimatedOutputTokens) ||
    estimatedOutputTokens < 0
  ) {
    throw new Error("GLM packed evidence cost inputs are invalid");
  }
  const estimatedNanoUsd =
    BigInt(estimatedInputTokens) *
      BigInt(DEEPINFRA_GLM_5_2_PRIORITY_NANO_USD.uncached_input) +
    BigInt(estimatedOutputTokens) *
      BigInt(DEEPINFRA_GLM_5_2_PRIORITY_NANO_USD.output);
  if (estimatedNanoUsd > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error("GLM packed evidence estimated cost exceeds the safe integer bound");
  }
  const estimatedCostUsd = Number(estimatedNanoUsd) / 1_000_000_000;
  return Object.freeze({
    prompt_chars: Number(promptChars),
    estimated_input_tokens: estimatedInputTokens,
    maximum_output_tokens: estimatedOutputTokens,
    estimated_cost_usd: estimatedCostUsd,
    cache_discount_assumed: false,
    service_tier: "priority",
    pricing_verified_on: GLM_FALLBACK.pricing.verified_on,
  });
}

function buildGlmPackedMessages(task, pack) {
  const prompt = buildWorkerPrompt(task);
  const packedContent = [
    GLM_PACKED_EVIDENCE_MODE,
    "The bridge already verified and receipted every required range below.",
    "Do not request tools. Use evidence_id and exact numbered lines for every governed citation.",
    "Return exactly one final JSON object with all required handoff fields.",
    JSON.stringify(pack),
  ].join("\n");
  const messages = [
    {
      role: "system",
      content: `${prompt.system}\nThis is a one-shot packed-evidence run; no tools are available.`,
    },
    { role: "user", content: prompt.user },
    { role: "user", content: packedContent },
  ];
  const promptChars = messages.reduce((total, message) => total + message.content.length, 0);
  if (promptChars > MAX_GLM_PACKED_PROMPT_CHARS) {
    throw new Error(
      `GLM packed evidence prompt exceeds ${MAX_GLM_PACKED_PROMPT_CHARS} characters`,
    );
  }
  return Object.freeze({ messages: Object.freeze(messages), promptChars, packedContent });
}

function buildFlashPackedMessages(task, pack) {
  const packedWrite = task.packedEvidenceMode === FLASH_PACKED_WRITE_MODE;
  const promptTask = task.contractHash
    ? task
    : { ...task, contractHash: buildContractHash(task) };
  const prompt = buildWorkerPrompt(promptTask);
  const packedSystem = prompt.system.replace(
    "Complete the task by calling finish_handoff exactly once with all required fields.",
    [
      "Return exactly one final JSON object; do not call finish_handoff or any tool.",
      `Required JSON keys: ${
        (packedWrite ? [...HANDOFF_KEYS, "write_operations"] : HANDOFF_KEYS).join(", ")
      }.`,
      "Use the status, execution_status, and evidence_verdict vocabularies in the task contract.",
      ...(packedWrite
        ? [
            (task.frozenArtifacts ?? []).length > 0
              ? "write_operations is the complete bounded mutation plan and may contain only strict replace_text, write_file, or write_frozen_file objects for exact allowed_paths. Reference every frozen_artifacts descriptor exactly once with write_frozen_file; never return inline content or content_base64 for that operation."
              : "write_operations is the complete bounded mutation plan and may contain only strict replace_text or write_file objects for exact allowed_paths.",
            "The host validates and stages the entire plan before applying it, then runs commands_tests; never claim host verification.",
            "Sol retains mandatory final acceptance even when this mechanical WRITE returns PASS.",
          ]
        : []),
    ].join("\n"),
  );
  const packedHandoffContract = [
    FLASH_PACKED_HANDOFF_SCHEMA_MARKER,
    JSON.stringify(FLASH_PACKED_HANDOFF_SCHEMA),
    "positive_findings and negative_findings MUST be JSON arrays, even when they contain " +
      "exactly one item. Every finding MUST be an exact {\"text\",\"citation\"} object.",
    "Each nested citation is the sole provider citation authority and must contain exactly " +
      "evidence_id, start, end, and unit. Do not emit a top-level citations member. " +
      "Use empty finding arrays when there are no findings.",
    FLASH_PACKED_HANDOFF_EXAMPLE_MARKER,
    JSON.stringify(FLASH_PACKED_HANDOFF_EXAMPLE),
  ].join("\n");
  const packedContent = [
    task.packedEvidenceMode,
    "The bridge already verified and receipted every required range below.",
    "Do not request tools. Use evidence_id and exact numbered lines for every governed citation.",
    packedWrite
      ? "Return exactly one final JSON object with all required handoff fields and write_operations."
      : "Return exactly one final JSON object with all required handoff fields.",
    JSON.stringify(pack),
  ].join("\n");
  const messages = [
    {
      role: "system",
      content:
        `${packedSystem}\n${packedHandoffContract}\n` +
        `This is a one-shot packed-evidence ${
          packedWrite ? "WRITE plan" : "run"
        }; no tools are available.`,
    },
    { role: "user", content: packedContent },
    { role: "user", content: prompt.user },
  ];
  const promptChars = messages.reduce((total, message) => total + message.content.length, 0);
  if (promptChars > MAX_GLM_PACKED_PROMPT_CHARS) {
    throw new Error(
      `Flash packed evidence prompt exceeds ${MAX_GLM_PACKED_PROMPT_CHARS} characters`,
    );
  }
  return Object.freeze({ messages: Object.freeze(messages), promptChars, packedContent });
}

function flashPackedStablePrefixIdentity(serializedBody, messages) {
  if (!Array.isArray(messages) || messages.length !== 3) {
    throw new Error("Flash packed evidence requires exactly three prompt messages");
  }
  const dynamicMessage = JSON.stringify(messages[2]);
  const dynamicOffset = serializedBody.lastIndexOf(dynamicMessage);
  if (dynamicOffset <= 0) {
    throw new Error("Flash packed evidence dynamic prompt boundary is unavailable");
  }
  const prefix = serializedBody.slice(0, dynamicOffset);
  return Object.freeze({
    stablePrefixHash: sha256(prefix),
    stablePrefixBytes: Buffer.byteLength(prefix, "utf8"),
  });
}

function safeNanoUsdBigInt(value, label) {
  if (value < 0n || value > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error(`${label} exceeds the safe integer bound`);
  }
  return Number(value);
}

function buildFlashPackedObservability({
  task,
  requestIdentityHash,
  stablePrefix,
  requestBodyBytes,
  estimate,
  reservation,
  pricing,
  usage = null,
  actualNanoUsd = null,
  reconciliationState,
  apiCalls,
  handoff = null,
}) {
  if (!/^CR-[a-f0-9]{32}$/.test(task.canaryRunId ?? "")) {
    throw new Error("Flash packed canary run identity is unavailable");
  }
  if (!/^[a-f0-9]{64}$/.test(task.projectHmac ?? "")) {
    throw new Error("Flash packed project HMAC is unavailable");
  }
  if (!/^[a-f0-9]{64}$/.test(requestIdentityHash ?? "")) {
    throw new Error("Flash packed request identity is unavailable");
  }
  if (
    !stablePrefix ||
    !/^[a-f0-9]{64}$/.test(stablePrefix.stablePrefixHash ?? "") ||
    !Number.isSafeInteger(stablePrefix.stablePrefixBytes) ||
    stablePrefix.stablePrefixBytes < 1
  ) {
    throw new Error("Flash packed stable-prefix identity is unavailable");
  }
  const reservedNanoUsd = Number(
    reservation?.reservedNanoUsd ?? estimate?.estimatedNanoUsd,
  );
  if (!Number.isSafeInteger(reservedNanoUsd) || reservedNanoUsd < 0) {
    throw new Error("Flash packed reserved cost is unavailable");
  }
  let actual = {
    prompt_tokens: null,
    cached_input_tokens: null,
    uncached_input_tokens: null,
    output_tokens: null,
    total_tokens: null,
    actual_nano_usd: null,
    uncached_equivalent_nano_usd: null,
    saved_nano_usd: null,
    cache_hit_ratio: null,
    reconciliation_state: reconciliationState ?? "UNKNOWN",
  };
  if (usage !== null) {
    const computedActual = nanoUsdCost(usage, pricing.rates);
    if (computedActual !== actualNanoUsd) {
      throw new Error("Flash packed observability actual cost is inconsistent");
    }
    const uncachedEquivalentNanoUsd = safeNanoUsdBigInt(
      BigInt(usage.prompt_tokens) * BigInt(pricing.rates.uncached_input) +
        BigInt(usage.completion_tokens) * BigInt(pricing.rates.output),
      "Flash packed uncached-equivalent cost",
    );
    const savedNanoUsd = safeNanoUsdBigInt(
      BigInt(usage.prompt_cache_hit_tokens) *
        BigInt(pricing.rates.uncached_input - pricing.rates.cached_input),
      "Flash packed saved cost",
    );
    if (computedActual + savedNanoUsd !== uncachedEquivalentNanoUsd) {
      throw new Error("Flash packed observability savings are inconsistent");
    }
    actual = {
      prompt_tokens: usage.prompt_tokens,
      cached_input_tokens: usage.prompt_cache_hit_tokens,
      uncached_input_tokens: usage.prompt_cache_miss_tokens,
      output_tokens: usage.completion_tokens,
      total_tokens: usage.total_tokens,
      actual_nano_usd: computedActual,
      uncached_equivalent_nano_usd: uncachedEquivalentNanoUsd,
      saved_nano_usd: savedNanoUsd,
      cache_hit_ratio:
        usage.prompt_tokens === 0
          ? 0
          : usage.prompt_cache_hit_tokens / usage.prompt_tokens,
      reconciliation_state: reconciliationState,
    };
  }
  return Object.freeze({
    event: "flash_packed_observability",
    schema_version: FLASH_PACKED_OBSERVABILITY_SCHEMA_VERSION,
    identity: Object.freeze({
      canary_run_id: task.canaryRunId,
      project_hmac: task.projectHmac,
      request_identity_hash: requestIdentityHash,
      stable_prefix_hash: stablePrefix.stablePrefixHash,
      prompt_schema_version: FLASH_PACKED_PROMPT_SCHEMA_VERSION,
      packed_evidence_mode: task.packedEvidenceMode,
      model: task.model,
      service_tier: task.serviceTier,
      frozen_artifact_policy_version: task.frozenArtifactPolicyVersion ?? null,
      frozen_artifact_payload_identity:
        task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
      frozen_artifacts: frozenArtifactDescriptors(task.frozenArtifacts),
    }),
    preflight: Object.freeze({
      request_body_bytes: requestBodyBytes,
      transport_body_limit_bytes: MAX_FLASH_PACKED_REQUEST_BODY_BYTES,
      transport_body_within_limit:
        requestBodyBytes <= MAX_FLASH_PACKED_REQUEST_BODY_BYTES,
      stable_prefix_bytes: stablePrefix.stablePrefixBytes,
      tokenizer_status: estimate.tokenizer?.tokenizer_status ?? "FAILED_CLOSED",
      tokenizer_failure_reason:
        estimate.tokenizer?.tokenizer_failure_reason ?? "tokenizer unavailable",
      tokenizer_model: estimate.tokenizer?.model ?? null,
      tokenizer_revision: estimate.tokenizer?.revision ?? null,
      tokenizer_package: estimate.tokenizer?.package ?? null,
      tokenizer_package_version:
        estimate.tokenizer?.package_version ?? null,
      tokenizer_artifact_sha256:
        estimate.tokenizer?.tokenizer_artifact_sha256 ?? null,
      tokenizer_config_sha256:
        estimate.tokenizer?.tokenizer_config_sha256 ?? null,
      tokenizer_encoding_sha256:
        estimate.tokenizer?.encoding_artifact_sha256 ?? null,
      tokenized_prompt_tokens:
        estimate.tokenizer?.tokenized_prompt_tokens ?? null,
      constraint_schema_tokens:
        estimate.tokenizer?.constraint_schema_tokens ?? null,
      tokenizer_margin_basis_points:
        estimate.tokenizer?.tokenizer_margin_basis_points ?? null,
      tokenizer_margin_fixed_tokens:
        estimate.tokenizer?.tokenizer_margin_fixed_tokens ?? null,
      tokenizer_margin_tokens:
        estimate.tokenizer?.tokenizer_margin_tokens ?? null,
      maximum_input_tokens: estimate.maximumInputTokens,
      maximum_output_tokens: task.maxOutputTokens,
      maximum_total_tokens: estimate.maximumInputTokens + task.maxOutputTokens,
      estimated_cost_nano_usd: estimate.estimatedNanoUsd,
      reserved_nano_usd: reservedNanoUsd,
      pricing_version: pricing.pricingVersion,
    }),
    actual: Object.freeze(actual),
    result: Object.freeze({
      api_calls: apiCalls,
      provider_route: "FLASH",
      execution_status: handoff?.execution_status ?? "BLOCKED",
      evidence_verdict: handoff?.evidence_verdict ?? "UNRESOLVED",
      coverage_status: handoff?.coverage_status ?? task.coverageStatus ?? "PENDING",
      local_exact_cache_outcome:
        task.reuseCache === false ? "BYPASSED_BY_CONTRACT" : "NOT_RECORDED",
      local_cache_rejection_codes: Object.freeze([]),
    }),
  });
}

export async function runDeepInfraGlmPackedAgent(
  task,
  {
    apiKey,
    fetchFunction,
    budgetController = null,
    signal,
    commandRunner,
    evidenceContext,
    audit,
  },
) {
  const controller = requireRouteBudgetController(budgetController, "GLM");
  const pricing = priceTuple(task, controller);
  const usage = emptyUsage();
  let apiCalls = 0;
  let providerStarted = false;
  let stage = "credential";
  let preflight = null;
  let reservation = null;
  const runtime = createRepositoryTools(task, { commandRunner, signal, evidenceContext });
  try {
    if (!String(apiKey ?? "").trim()) throw new Error(`${task.credentialEnv} is not configured`);
    if (typeof fetchFunction !== "function") throw new Error("direct HTTP fetch is unavailable");
    stage = "evidence_pack";
    const pack = runtime.packRequiredEvidence();
    stage = "pack_size";
    const built = buildGlmPackedMessages(task, pack);
    stage = "cost_gate";
    preflight = estimateGlmPackedCost(built.promptChars, task.maxOutputTokens);
    if (preflight.estimated_cost_usd > task.routeConstraints.maximumEstimatedCostUsd) {
      throw new Error(
        `GLM packed evidence estimated cost ${preflight.estimated_cost_usd.toFixed(6)} USD ` +
          `exceeds contract ceiling ${task.routeConstraints.maximumEstimatedCostUsd.toFixed(6)} USD`,
      );
    }
    audit({
      event: "glm_packed_evidence_preflight",
      status: "READY",
      stage: "cost_gate",
      manifest_hash: pack.manifest_hash,
      pack_hash: pack.pack_hash,
      section_count: pack.sections.length,
      ...preflight,
    });

    const canonicalRequest = buildDeepSeekRequest(
      task,
      built.messages,
      [],
      { forceFinal: true },
    );
    const serializedBody = JSON.stringify(canonicalRequest);
    const requestIdentityHash = sha256(serializedBody);
    const maximumEstimate = maximumEstimatedNanoUsd(
      serializedBody,
      task.maxOutputTokens,
      pricing.rates,
    );
    stage = "cost_reservation";
    reservation = await controller.reserveNextCall({
      task,
      projectId: task.projectId ?? "UNSCOPED",
      jobId: task.jobId ?? task.taskId ?? "UNASSIGNED",
      attemptId: task.attemptId ?? "UNASSIGNED",
      turn: 1,
      requestIdentityHash,
      canonicalRequest,
      messages: built.messages,
      maximumOutputTokens: task.maxOutputTokens,
      maximumInputTokens: maximumEstimate.maximumInputTokens,
      estimatedNanoUsd: maximumEstimate.estimatedNanoUsd,
      pricing,
      costPolicyVersion: COST_POLICY_VERSION,
    });
    if (signal?.aborted) {
      await controller.reconcile(reservation, {
        outcome: "RELEASED",
        usage: null,
        actualNanoUsd: 0,
        costPolicyVersion: COST_POLICY_VERSION,
        pricingVersion: pricing.pricingVersion,
      });
      const aborted = new Error("provider request was cancelled before transmission");
      aborted.name = "AbortError";
      Object.defineProperties(aborted, {
        executionStatus: { value: "CANCELLED", enumerable: true },
        deepseekFailureClass: { value: "LOCAL_CONTRACT" },
        providerStarted: { value: false },
      });
      throw aborted;
    }

    stage = "provider_request";
    providerStarted = true;
    apiCalls = 1;
    let response;
    try {
      response = await fetchFunction(task.apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: serializedBody,
        signal,
      });
    } catch (error) {
      await reconcileUnknown(controller, reservation);
      if (error?.name === "AbortError") {
        throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_AFTER_ABORT");
      }
      const networkError = new Error(
        `GLM-5.2 API network failure: ${safeDiagnosticText(error, [apiKey])}`,
      );
      throw accountingUncertainError(networkError, "ACCOUNTING_UNKNOWN_AFTER_FETCH");
    }
    stage = "provider_response";
    if (!response.ok) {
      const failure = apiFailure(response.status, "GLM-5.2 API");
      if (isDeterministicRequestRejection(failure)) {
        await controller.reconcile(reservation, {
          outcome: "RELEASED",
          usage: null,
          actualNanoUsd: 0,
          costPolicyVersion: COST_POLICY_VERSION,
          pricingVersion: pricing.pricingVersion,
        });
        throw failure;
      }
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(failure, "ACCOUNTING_UNKNOWN_AFTER_HTTP");
    }
    let responseText;
    try {
      responseText = await response.text();
    } catch (error) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_DURING_BODY_READ");
    }
    stage = "response_parse";
    let payload;
    try {
      payload = JSON.parse(responseText.trim());
    } catch (error) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_MALFORMED_2XX");
    }
    const choice = payload?.choices?.[0];
    const message = choice?.message;
    if (!message || message.role !== "assistant") {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(
        new Error("GLM-5.2 API response did not contain an assistant message"),
        "PROVIDER_OUTPUT_UNKNOWN",
      );
    }
    let normalizedUsage;
    let actualNanoUsd;
    try {
      normalizedUsage = strictProviderUsage(payload.usage);
      actualNanoUsd = nanoUsdCost(normalizedUsage, pricing.rates);
    } catch (error) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(error, "ACCOUNTING_UNKNOWN_INVALID_USAGE");
    }
    addUsage(usage, normalizedUsage);
    audit({
      event: "glm_packed_evidence_response",
      status: "RECEIVED",
      stage: "provider_response",
      response_id: payload.id ?? null,
      model: payload.model ?? task.model,
      finish_reason: choice.finish_reason ?? null,
      usage: payload.usage ?? {},
      service_tier: payload.service_tier ?? null,
    });
    if (choice.finish_reason === "length") {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(
        new Error("GLM-5.2 packed evidence output was truncated"),
        "PROVIDER_OUTPUT_UNKNOWN",
      );
    }
    if (hasDegenerateRepeatedSpan(message.content)) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(
        new Error("GLM-5.2 returned a degenerate repeated span"),
        "PROVIDER_OUTPUT_UNKNOWN",
      );
    }
    if (Array.isArray(message.tool_calls) && message.tool_calls.length > 0) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(
        new Error("GLM-5.2 returned tool calls during a tool-free packed-evidence run"),
        "PROVIDER_OUTPUT_UNKNOWN",
      );
    }
    stage = "handoff_validation";
    let handoff;
    try {
      const candidate = parseCandidate(message.content);
      handoff = redactDiagnostic(normalizeHandoff(candidate, task, runtime), [apiKey]);
    } catch (error) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(error, "PROVIDER_OUTPUT_UNKNOWN");
    }
    try {
      await controller.reconcile(reservation, {
        outcome: "RECONCILED",
        usage: normalizedUsage,
        actualNanoUsd,
        costPolicyVersion: COST_POLICY_VERSION,
        pricingVersion: pricing.pricingVersion,
      });
    } catch (error) {
      await reconcileUnknown(controller, reservation);
      throw accountingUncertainError(error);
    }
    audit({
      event: "glm_packed_evidence_complete",
      status: handoff.status,
      stage: "handoff_validation",
      coverage_status: handoff.coverage_status,
      api_calls: apiCalls,
      manifest_hash: pack.manifest_hash,
      pack_hash: pack.pack_hash,
    });
    return {
      handoff,
      usage,
      api_calls: apiCalls,
      service_tier: payload.service_tier ?? null,
      packed_evidence: {
        mode: GLM_PACKED_EVIDENCE_MODE,
        manifest_hash: pack.manifest_hash,
        pack_hash: pack.pack_hash,
        section_count: pack.sections.length,
        ...preflight,
      },
    };
  } catch (error) {
    if (stage === "evidence_pack" && /stale manifest/i.test(error?.message ?? "")) {
      stage = "manifest_freshness";
    }
    const normalized = error instanceof Error ? error : new Error(String(error));
    if (!providerStarted && !normalized.deepseekFailureClass) {
      Object.defineProperty(normalized, "deepseekFailureClass", {
        value: "LOCAL_CONTRACT",
        enumerable: false,
      });
    }
    if (!providerStarted) {
      Object.defineProperty(normalized, "glmPreflightBlocked", {
        value: true,
        enumerable: false,
      });
      Object.defineProperty(normalized, "lunaProviderStarted", {
        value: false,
        enumerable: false,
      });
      Object.defineProperty(normalized, "fallbackProviderStarted", {
        value: false,
        enumerable: false,
      });
    }
    audit({
      event: "glm_packed_evidence_failure",
      status: "BLOCKED",
      stage,
      provider_started: providerStarted,
      api_calls: apiCalls,
      error: safeDiagnosticText(normalized, [apiKey]),
      ...(preflight ?? {}),
    });
    throw attachRunMetrics(normalized, usage, apiCalls);
  }
}

export async function runDeepInfraGlmAgent(
  task,
  {
    apiKey = resolvePrimaryApiKey(resolvePrimaryProfile("deepinfra-fast")),
    fetchFunction = globalThis.fetch,
    budgetController = null,
    signal,
    commandRunner,
    evidenceContext = null,
    audit = () => {},
  } = {},
) {
  const routeController = requireRouteBudgetController(budgetController, "GLM");
  const started = Date.now();
  if (task.mode !== "READ_ONLY" || task.packedEvidenceMode !== GLM_PACKED_EVIDENCE_MODE) {
    throw new Error("GLM-5.2 requires packed evidence in READ_ONLY mode");
  }
  const deepinfra = resolvePrimaryProfile("deepinfra-fast");
  const glmTask = Object.freeze({
    ...task,
    model: GLM_FALLBACK.model,
    primaryProfile: deepinfra.id,
    primaryProvider: deepinfra.provider,
    primaryRoute: deepinfra.route,
    primaryDisplayName: "GLM-5.2",
    apiUrl: deepinfra.apiUrl,
    credentialEnv: deepinfra.credentialEnv,
    requestDialect: deepinfra.requestDialect,
    serviceTier: deepinfra.serviceTier,
    reasoningEffort: GLM_FALLBACK.reasoning,
    routeConstraints: Object.freeze({
      ...task.routeConstraints,
      maximumProviderCalls: 1,
    }),
    maxOutputTokens: Math.min(task.maxOutputTokens, GLM_FALLBACK.maxOutputTokens),
  });
  const response = await runDeepInfraGlmPackedAgent(glmTask, {
    apiKey,
    fetchFunction,
    budgetController: routeController,
    signal,
    commandRunner,
    evidenceContext,
    audit,
  });
  return {
    ...response,
    provider: GLM_FALLBACK.provider,
    model: GLM_FALLBACK.model,
    reasoning: GLM_FALLBACK.reasoning,
    chatgpt_subscription: false,
    exit_code: 0,
    elapsed_ms: Date.now() - started,
  };
}

export async function runFallbackAgent(task, options = {}) {
  if (task?.localExactWrite === true) {
    const error = new Error("LOCAL exact-byte WRITE cannot use a fallback provider");
    Object.defineProperty(error, "lunaProviderStarted", {
      value: false,
      enumerable: false,
    });
    throw error;
  }
  const fallbackRoute = normalizeFallbackRoute(options.fallbackRoute ?? "LUNA");
  requireRouteBudgetController(options.budgetController, fallbackRoute);
  if (fallbackRoute === "GLM") {
    return runDeepInfraGlmAgent(task, options);
  }
  return runCodexLunaAgent(task, { ...options, fallbackRoute });
}

function defaultStoreRoot() {
  return path.resolve(
    process.env.DEEPSEEK_ORCHESTRATOR_HOME ??
      path.join(process.env.LOCALAPPDATA ?? os.homedir(), "Codex", "deepseek-orchestrator"),
  );
}

function jobId() {
  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace("Z", "Z");
  return `DS-${timestamp}-${crypto.randomBytes(3).toString("hex")}`;
}

function legacyResultSemantics(status, result = null) {
  if (result?.execution_status && result?.evidence_verdict) {
    return {
      execution_status: result.execution_status,
      evidence_verdict: result.evidence_verdict,
    };
  }
  if (new Set(["PASS", "CACHED"]).has(status)) {
    return { execution_status: "ACCEPTED", evidence_verdict: "NOT_APPLICABLE" };
  }
  if (status === "BLOCKED") {
    return { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" };
  }
  return { execution_status: "INCOMPLETE", evidence_verdict: "UNRESOLVED" };
}

function withResultSemantics(candidate) {
  const normalized = normalizeResult({
    ...candidate,
    status: candidate?.status ? String(candidate.status).toUpperCase() : undefined,
    execution_status: candidate?.execution_status
      ? String(candidate.execution_status).toUpperCase()
      : undefined,
    evidence_verdict: candidate?.evidence_verdict
      ? String(candidate.evidence_verdict).toUpperCase()
      : undefined,
  });
  return {
    ...candidate,
    status: legacyStatus(normalized),
    execution_status: normalized.execution_status,
    evidence_verdict: normalized.evidence_verdict,
  };
}

function primaryRoutePolicyKey(task) {
  if (task.tier === "FLASH") return "FLASH";
  if (!isDeepInfraProfile(task.primaryProfile)) return "DIRECT_PRO";
  return task.tier === "REASONING" ? "NEMOTRON" : "V4_PRO";
}

function shouldUseLocalRoute(task) {
  const allowedRoutes = task?.routeConstraints?.allowedRoutes ?? [];
  if (task?.mode === "WRITE") return task.localExactWrite === true;
  if (task?.mode !== "READ_ONLY") return false;
  if (!Array.isArray(allowedRoutes) || !allowedRoutes.includes("LOCAL")) return false;
  if (task.routeConstraints?.privacyClass === "LOCAL_ONLY") return true;
  return allowedRoutes.length === 1 && allowedRoutes[0] === "LOCAL";
}

function isLocalRoute(route) {
  return String(route ?? "").toUpperCase() === "LOCAL";
}

function publicJobState(job, result = null, { includeHandoff = false } = {}) {
  const semantics = legacyResultSemantics(result?.status ?? job.status, result);
  const response = {
    job_id: job.job_id,
    evidence_id: job.job_id,
    status: job.status,
    ...semantics,
    mode: job.mode,
    tier: job.tier,
    model: job.model ?? null,
    provider: job.provider ?? null,
    submitted_at: job.submitted_at,
    started_at: job.started_at ?? null,
    finished_at: job.finished_at ?? null,
    cache_hit: Boolean(job.cache_hit),
    coalesced: Boolean(job.coalesced),
    coverage_status: result?.coverage_status ?? job.coverage_status ?? null,
  };
  if (result) {
    response.summary = boundedText(result.summary ?? "", 800);
    if (includeHandoff === true) {
      const handoff = productionWorkerHandoff(result);
      response.positive_findings = handoff.positive_findings;
      response.negative_findings = handoff.negative_findings;
      response.residual_risks = handoff.residual_risks;
      response.recommended_next_action = handoff.recommended_next_action;
      response.scientific_uncertainty = handoff.scientific_uncertainty;
      response.architecture_uncertainty = handoff.architecture_uncertainty;
      response.scope_deviation = handoff.scope_deviation;
    }
    if (typeof result.error_code === "string") response.error_code = result.error_code;
    response.usage = result.usage;
    response.api_calls = result.api_calls;
    response.provider_route = result.provider_route;
    response.fallback = result.fallback
      ? {
          used: Boolean(result.fallback.used),
          reason: result.fallback.reason ?? null,
          attempt: Number(result.fallback.attempt) || 0,
        }
      : null;
    response.provider_usage = result.provider_usage;
  }
  return response;
}

function lunaUsageEvidence(response) {
  return {
    chatgpt_subscription: Boolean(response.chatgpt_subscription),
    model: response.model ?? null,
    reasoning: response.reasoning ?? null,
    exit_code: Number(response.exit_code) || 0,
    elapsed_ms: Number(response.elapsed_ms) || 0,
    usage: response.usage ?? parseCodexJsonUsage(""),
  };
}

function normalizeFallbackUsage(rawUsage = null) {
  const usage = typeof rawUsage === "object" && rawUsage ? rawUsage : {};
  const inputTokens = Number(usage.prompt_tokens);
  if (Number.isFinite(inputTokens)) {
    return {
      input_tokens: inputTokens,
      cached_input_tokens: Number(usage.prompt_cache_hit_tokens) || 0,
      output_tokens: Number(usage.completion_tokens) || 0,
      reasoning_output_tokens: Number(usage.reasoning_output_tokens) || 0,
      total_tokens: Number(usage.total_tokens)
        || Number(usage.prompt_tokens) + Number(usage.completion_tokens) || 0,
    };
  }
  return {
    input_tokens: Number(usage.input_tokens) || 0,
    cached_input_tokens: Number(usage.cached_input_tokens) || 0,
    output_tokens: Number(usage.output_tokens) || 0,
    reasoning_output_tokens: Number(usage.reasoning_output_tokens) || 0,
    total_tokens: Number(usage.total_tokens) || 0,
  };
}

function fallbackProviderEvidence(response, fallbackRoute = "LUNA") {
  return {
    chatgpt_subscription: Boolean(response?.chatgpt_subscription),
    model: response?.model ?? null,
    reasoning: response?.reasoning ?? null,
    exit_code: Number(response?.exit_code) || 0,
    elapsed_ms: Number(response?.elapsed_ms) || 0,
    usage: normalizeFallbackUsage(response?.usage),
    ...(response?.packed_evidence
      ? { packed_evidence: response.packed_evidence }
      : {}),
  };
}

function headJobId() {
  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace("Z", "Z");
  return `SH-${timestamp}-${crypto.randomBytes(3).toString("hex")}`;
}

function headPublicJobState(job, result = null) {
  const semantics = legacyResultSemantics(result?.status ?? job.status, result);
  const response = {
    job_id: job.job_id,
    plan_id: job.plan_id,
    evidence_id: job.job_id,
    status: job.status,
    ...semantics,
    mode: "READ_ONLY",
    model: job.model,
    requested_effort: job.requested_effort,
    actual_effort: result?.actual_effort ?? null,
    submitted_at: job.submitted_at,
    started_at: job.started_at ?? null,
    finished_at: job.finished_at ?? null,
    cache_hit: Boolean(job.cache_hit),
    coalesced: Boolean(job.coalesced),
  };
  if (result) {
    response.summary = boundedText(result.summary ?? "", 800);
    response.usage = result.usage;
    response.api_calls = result.api_calls;
    response.model_calls = result.model_calls;
    response.provider_route = result.provider_route;
    response.provider_usage = result.provider_usage;
  }
  return response;
}

export class HeadJobManager {
  constructor({
    storeRoot = defaultStoreRoot(),
    projectId = process.env.DEEPLUNA_PROJECT_ID,
    projectScope = process.env.DEEPLUNA_PROJECT_SCOPE,
    originThreadId = process.env.CODEX_THREAD_ID,
    originContext = null,
    projectSecretFactory = crypto.randomBytes,
    solRunner = runCodexSolHeadAgent,
    budgetController = null,
    routingPolicy = DEFAULT_HEAD_ROUTING_POLICY,
    headSchemaVersion = 1,
    timerFunction = setTimeout,
    clearTimerFunction = clearTimeout,
    allowedRoots = null,
    primaryProfile = resolvePrimaryProfile(),
  } = {}) {
    this.baseStoreRoot = path.resolve(storeRoot);
    this.storeRoot = this.baseStoreRoot;
    this.projectScope = resolveProjectScope(projectScope);
    this.projectId = resolveProjectId(projectId, process.cwd());
    const projectRoot = path.join(this.baseStoreRoot, "projects", this.projectId);
    const projectSecret = ensureProjectSecret(projectRoot, projectSecretFactory);
    this.projectSecret = projectSecret;
    this.origin = originContext ?? deriveOriginContext(
      originThreadId ?? `local-${process.pid}-${crypto.randomUUID()}`,
      projectSecret,
    );
    const scoped = projectStorePaths(this.baseStoreRoot, this.projectId, {
      scope: this.projectScope,
      threadScope: this.origin.originThreadHash,
    });
    this.projectRoot = scoped.projectRoot;
    this.headsRoot = scoped.headsRoot;
    this.plansRoot = path.join(this.headsRoot, "plans");
    this.jobsRoot = path.join(this.headsRoot, "jobs");
    this.cacheRoot = path.join(this.headsRoot, "cache");
    this.lockRoot = path.join(this.headsRoot, "locks");
    this.statePath = path.join(this.headsRoot, "state-v1.json");
    this.stateLockPath = path.join(this.headsRoot, "state-v1.lock");
    this.solRunner = solRunner;
    this.budgetController = budgetController;
    this.timerFunction = timerFunction;
    this.clearTimerFunction = clearTimerFunction;
    this.allowedRoots = allowedRoots;
    this.primaryProfile = primaryProfile;
    this.routingPolicy = Object.freeze({
      ...DEFAULT_HEAD_ROUTING_POLICY,
      ...(routingPolicy ?? {}),
    });
    this.headSchemaVersion = Number(headSchemaVersion);
    if (!Number.isInteger(this.headSchemaVersion) || this.headSchemaVersion < 1) {
      throw new Error("headSchemaVersion must be a positive integer");
    }
    for (const directory of [this.plansRoot, this.jobsRoot, this.cacheRoot, this.lockRoot]) {
      mkdirSync(directory, { recursive: true });
    }
    this.active = new Map();
    if (!existsSync(this.statePath)) this.mutateState(() => {});
    removeStaleLocks(this.lockRoot);
    this.recoverInterruptedJobs();
  }

  policyHash() {
    return sha256(stableJson({
      identity: SOL_HEAD.policy,
      routingPolicy: this.routingPolicy,
      headSchemaVersion: this.headSchemaVersion,
    }));
  }

  governancePaths(workspace) {
    return [".codex/cost_policy.json", "AGENTS.md", "RULES.md"]
      .filter((relative) => existsSync(path.resolve(workspace, relative)))
      .map((relative) => normalizeAllowedPath(workspace, relative))
      .sort();
  }

  async plan(raw) {
    const validatedInput = validateSolRoutePlanInput(raw, {
      projectId: this.projectId,
      projectScope: this.projectScope,
      allowedRoots: this.allowedRoots,
      primaryProfile: this.primaryProfile,
    });
    const task = validatedInput.task;
    if (task.allowedPaths.length === 0) {
      throw new Error("Sol head route plans require at least one allowed path");
    }
    const route = classifySolRoute(validatedInput.input, this.routingPolicy);
    const routeContract = buildSolRouteContract(validatedInput.input, route);
    const governancePaths = this.governancePaths(task.workspace);
    const evidenceHash = await fingerprintAllowedPaths(task.workspace, task.allowedPaths);
    const governanceHash = await fingerprintAllowedPaths(task.workspace, governancePaths);
    const policyHash = this.policyHash();
    const outputSchemaHash = sha256(stableJson(headHandoffSchema()));
    const normalizedTask = {
      objective: task.objective,
      mode: "READ_ONLY",
      workspace: task.workspace,
      allowedPaths: task.allowedPaths,
      forbiddenActions: task.forbiddenActions,
      commandsTests: task.commandsTests,
      definitionOfDone: task.definitionOfDone,
      requiredOutput: task.requiredOutput,
      timeoutMs: task.timeoutMs,
      maxOutputTokens: task.maxOutputTokens,
      reuseCache: task.reuseCache,
    };
    const identity = {
      plan_version: 1,
      project_id: this.projectId,
      ...this.origin,
      bridge_version: VERSION,
      schema_version: this.headSchemaVersion,
      output_schema_hash: outputSchemaHash,
      provider: SOL_HEAD.provider,
      model: SOL_HEAD.model,
      route,
      route_contract: routeContract,
      policy_hash: policyHash,
      evidence_hash: evidenceHash,
      governance_hash: governanceHash,
      governance_paths: governancePaths,
      task: normalizedTask,
    };
    identity.max_attempt_key = route.max_eligible
      ? sha256(stableJson({
        policy_hash: policyHash,
        output_schema_hash: outputSchemaHash,
        provider: SOL_HEAD.provider,
        model: SOL_HEAD.model,
        selected_effort: route.selected_effort,
        evidence_hash: evidenceHash,
        governance_hash: governanceHash,
        route_contract: routeContract,
        objective: normalizedTask.objective,
        allowed_paths: normalizedTask.allowedPaths,
        forbidden_actions: normalizedTask.forbiddenActions,
        commands_tests: normalizedTask.commandsTests,
        definition_of_done: normalizedTask.definitionOfDone,
        required_output: normalizedTask.requiredOutput,
      }))
      : null;
    const planId = `SRP-${sha256(stableJson(identity)).slice(0, 32)}`;
    const planPath = path.join(this.plansRoot, `${planId}.json`);
    if (!existsSync(planPath)) {
      atomicJson(planPath, {
        plan_id: planId,
        created_at: new Date().toISOString(),
        ...identity,
      });
    }
    return Object.freeze({
      plan_id: planId,
      evidence_id: planId,
      action: route.action,
      switch_scope: route.switch_scope,
      selected_effort: route.selected_effort,
      policy_hash: policyHash,
      evidence_hash: evidenceHash,
      governance_hash: governanceHash,
      provider_calls: 0,
    });
  }

  defaultState() {
    return { version: 1, max_attempts: {} };
  }

  readState() {
    try {
      const raw = readJson(this.statePath);
      if (raw.version !== 1 || !raw.max_attempts || typeof raw.max_attempts !== "object") {
        return this.defaultState();
      }
      return { version: 1, max_attempts: { ...raw.max_attempts } };
    } catch {
      return this.defaultState();
    }
  }

  mutateState(mutator) {
    const release = acquireStateLock(this.stateLockPath);
    try {
      const state = this.readState();
      mutator(state);
      atomicJson(this.statePath, state);
      return state;
    } finally {
      release();
    }
  }

  loadPlan(id) {
    if (!/^SRP-[a-f0-9]{32}$/.test(String(id ?? ""))) {
      throw new Error("invalid Sol head plan_id");
    }
    const planPath = path.join(this.plansRoot, `${id}.json`);
    if (!existsSync(planPath)) throw new Error(`unknown Sol head plan_id: ${id}`);
    const plan = readJson(planPath);
    const { plan_id: storedId, created_at: _createdAt, ...identity } = plan;
    const reconstructed = `SRP-${sha256(stableJson(identity)).slice(0, 32)}`;
    if (storedId !== id || reconstructed !== id) {
      throw new Error("Sol head plan identity verification failed");
    }
    assertOriginOwns(plan, this.origin);
    if (plan.bridge_version !== VERSION) {
      throw new Error("Sol head plan bridge version is stale");
    }
    if (plan.schema_version !== this.headSchemaVersion) {
      throw new Error("Sol head plan schema version is stale");
    }
    if (plan.output_schema_hash !== sha256(stableJson(headHandoffSchema()))) {
      throw new Error("Sol head plan output schema changed");
    }
    if (plan.policy_hash !== this.policyHash()) {
      throw new Error("Sol head plan routing policy changed");
    }
    return plan;
  }

  claimMaxAttempt(plan, id) {
    if (!plan.route.max_eligible) return;
    if (!plan.max_attempt_key) throw new Error("Max plan is missing its attempt identity");
    this.mutateState((state) => {
      const existing = state.max_attempts[plan.max_attempt_key];
      if (
        existing?.job_id === id &&
        existing?.plan_id === plan.plan_id
      ) {
        return;
      }
      if (existing) {
        throw new Error(
          `one-shot Max attempt already recorded for this route: ${existing.job_id}`,
        );
      }
      state.max_attempts[plan.max_attempt_key] = {
        job_id: id,
        plan_id: plan.plan_id,
        started_at: new Date().toISOString(),
      };
    });
  }

  cachedResult(plan) {
    if (!plan.task.reuseCache) return null;
    const cachePath = path.join(this.cacheRoot, `${plan.plan_id}.json`);
    if (!existsSync(cachePath)) return null;
    const cached = readJson(cachePath);
    if (cached.plan_id !== plan.plan_id || cached.status !== "PASS") {
      throw new Error("Sol head cache identity or status is invalid");
    }
    return { cachePath, cached };
  }

  async assertCurrentInputs(plan) {
    const executionTask = headExecutionTask(plan);
    const evidenceHash = await fingerprintAllowedPaths(
      executionTask.workspace,
      plan.task.allowedPaths,
    );
    if (evidenceHash !== plan.evidence_hash) {
      throw new Error("Sol head plan evidence changed after planning");
    }
    const governanceHash = await fingerprintAllowedPaths(
      executionTask.workspace,
      plan.governance_paths,
    );
    if (governanceHash !== plan.governance_hash) {
      throw new Error("Sol head governance changed after planning");
    }
  }

  materializeCacheHit(plan, cache, id = headJobId()) {
    const directory = path.join(this.jobsRoot, id);
    mkdirSync(directory, { recursive: true });
    const resultPath = path.join(directory, "result.json");
    const now = new Date().toISOString();
    const result = {
      ...cache.cached,
      job_id: id,
      status: "CACHED",
      cache_hit: true,
      finished_at: now,
      result_path: resultPath,
      source_cache_path: cache.cachePath,
      model_calls: 0,
    };
    const job = {
      job_id: id,
      plan_id: plan.plan_id,
      status: "CACHED",
      model: SOL_HEAD.model,
      requested_effort: plan.route.selected_effort,
      submitted_at: now,
      finished_at: now,
      cache_hit: true,
      job_directory: directory,
      ...this.origin,
    };
    atomicJson(resultPath, result);
    atomicJson(path.join(directory, "job.json"), job);
    return headPublicJobState(job, result);
  }

  materializeBudgetBlocked(plan, error, id = headJobId()) {
    const directory = path.join(this.jobsRoot, id);
    mkdirSync(directory, { recursive: true });
    const resultPath = path.join(directory, "result.json");
    const now = new Date().toISOString();
    const handoff = this.failureHandoff(error);
    const result = {
      job_id: id,
      plan_id: plan.plan_id,
      status: "BLOCKED",
      execution_status: "BLOCKED",
      evidence_verdict: "UNRESOLVED",
      summary: handoff.summary,
      head_handoff: handoff,
      model: SOL_HEAD.model,
      requested_effort: plan.route.selected_effort,
      actual_effort: "UNVERIFIED",
      cache_hit: false,
      finished_at: now,
      usage: parseCodexJsonUsage(""),
      api_calls: 0,
      model_calls: 0,
      provider_route: [],
      provider_usage: { sol: null },
      result_path: resultPath,
    };
    const job = {
      job_id: id,
      plan_id: plan.plan_id,
      status: "BLOCKED",
      model: SOL_HEAD.model,
      requested_effort: plan.route.selected_effort,
      submitted_at: now,
      finished_at: now,
      cache_hit: false,
      job_directory: directory,
      ...this.origin,
    };
    atomicJson(resultPath, result);
    atomicJson(path.join(directory, "job.json"), job);
    return headPublicJobState(job, result);
  }

  async submit(planId) {
    const plan = this.loadPlan(planId);
    assertSolHeadPlan(plan);
    await this.assertCurrentInputs(plan);
    const cache = this.cachedResult(plan);
    if (cache) return this.materializeCacheHit(plan, cache);
    try {
      requireRouteBudgetController(this.budgetController, "SOL");
    } catch (error) {
      return this.materializeBudgetBlocked(plan, error);
    }

    const id = headJobId();
    const taskLock = acquireTaskLock(this.lockRoot, plan.plan_id, id);
    if (!taskLock.acquired) {
      try {
        return { ...this.status(taskLock.job_id), coalesced: true };
      } catch {
        return {
          job_id: taskLock.job_id,
          plan_id: plan.plan_id,
          status: "RUNNING",
          cache_hit: false,
          coalesced: true,
        };
      }
    }

    let releaseSlot;
    try {
      try {
        releaseSlot = acquireSlot(this.lockRoot, "WRITE");
      } catch (error) {
        if (/writer is active|active readers|concurrency gate is busy/i.test(error?.message ?? "")) {
          throw new Error("a Sol head job is active");
        }
        throw error;
      }
      this.claimMaxAttempt(plan, id);
      const directory = path.join(this.jobsRoot, id);
      mkdirSync(directory, { recursive: true });
      atomicJson(path.join(directory, "request.json"), {
        plan_id: plan.plan_id,
        ...this.origin,
        provider: SOL_HEAD.provider,
        model: SOL_HEAD.model,
        requested_effort: plan.route.selected_effort,
        policy_hash: plan.policy_hash,
        evidence_hash: plan.evidence_hash,
        governance_hash: plan.governance_hash,
      });
      const startedAt = new Date().toISOString();
      const job = {
        job_id: id,
        plan_id: plan.plan_id,
        status: "RUNNING",
        model: SOL_HEAD.model,
        requested_effort: plan.route.selected_effort,
        submitted_at: startedAt,
        started_at: startedAt,
        cache_hit: false,
        owner_pid: process.pid,
        job_directory: directory,
        ...this.origin,
      };
      atomicJson(path.join(directory, "job.json"), job);
      const controller = new AbortController();
      const active = {
        controller,
        releaseSlot,
        releaseTaskLock: taskLock.release,
        plan,
        directory,
        cancelled: false,
        timedOut: false,
        timeoutHandle: null,
      };
      this.active.set(id, active);
      active.timeoutHandle = this.timerFunction(() => {
        const current = this.active.get(id);
        if (!current) return;
        current.timedOut = true;
        current.controller.abort();
      }, plan.task.timeoutMs);
      active.timeoutHandle?.unref?.();
      void this.runActiveJob(id, job, active);
      return headPublicJobState(job);
    } catch (error) {
      releaseSlot?.();
      taskLock.release();
      throw error;
    }
  }

  async runPlannedJob(planId, options = {}) {
    if (
      options === null ||
      typeof options !== "object" ||
      Array.isArray(options) ||
      Object.getPrototypeOf(options) !== Object.prototype
    ) {
      throw new TypeError("planned Sol job options must be a plain object");
    }
    const descriptors = Object.getOwnPropertyDescriptors(options);
    const optionKeys = Reflect.ownKeys(descriptors);
    if (
      optionKeys.some(
        (key) =>
          typeof key !== "string" ||
          !["jobId", "beforeExternalStart"].includes(key) ||
          descriptors[key].enumerable !== true ||
          !Object.hasOwn(descriptors[key], "value"),
      ) ||
      !Object.hasOwn(descriptors, "jobId")
    ) {
      throw new TypeError("planned Sol job options have an invalid shape");
    }
    const id = descriptors.jobId.value;
    if (typeof id !== "string" || !/^SH-[a-f0-9]{32}$/.test(id)) {
      throw new TypeError("planned Sol jobId must be a deterministic SH identity");
    }
    const beforeExternalStart = Object.hasOwn(
      descriptors,
      "beforeExternalStart",
    )
      ? descriptors.beforeExternalStart.value
      : null;
    if (
      beforeExternalStart !== null &&
      typeof beforeExternalStart !== "function"
    ) {
      throw new TypeError("beforeExternalStart must be a function");
    }
    const plan = this.loadPlan(planId);
    assertSolHeadPlan(plan);
    const directory = path.join(this.jobsRoot, id);
    const jobPath = path.join(directory, "job.json");
    const resultPath = path.join(directory, "result.json");
    if (existsSync(jobPath)) {
      const existingJob = readJson(jobPath);
      if (
        existingJob.job_id !== id ||
        existingJob.plan_id !== plan.plan_id
      ) {
        throw new Error("planned Sol job identity conflicts with durable files");
      }
      assertOriginOwns(existingJob, this.origin);
      if (existsSync(resultPath)) {
        return headPublicJobState(existingJob, readJson(resultPath));
      }
      const active = this.active.get(id);
      if (active?.completion) return active.completion;
      throw new Error("planned Sol job has an unresolved active artifact");
    }
    await this.assertCurrentInputs(plan);
    const cache = this.cachedResult(plan);
    if (cache) return this.materializeCacheHit(plan, cache, id);
    try {
      requireRouteBudgetController(this.budgetController, "SOL");
    } catch (error) {
      return this.materializeBudgetBlocked(plan, error, id);
    }

    const taskLock = acquireTaskLock(this.lockRoot, plan.plan_id, id);
    if (!taskLock.acquired) {
      const active = this.active.get(taskLock.job_id);
      if (active?.completion) return active.completion;
      return this.status(taskLock.job_id);
    }
    let releaseSlot;
    let activeOwnsReleases = false;
    try {
      try {
        releaseSlot = acquireSlot(this.lockRoot, "WRITE");
      } catch (error) {
        if (
          /writer is active|active readers|concurrency gate is busy/i.test(
            error?.message ?? "",
          )
        ) {
          throw new Error("a Sol head job is active");
        }
        throw error;
      }
      this.claimMaxAttempt(plan, id);
      mkdirSync(directory, { recursive: true });
      atomicJson(path.join(directory, "request.json"), {
        plan_id: plan.plan_id,
        ...this.origin,
        provider: SOL_HEAD.provider,
        model: SOL_HEAD.model,
        requested_effort: plan.route.selected_effort,
        policy_hash: plan.policy_hash,
        evidence_hash: plan.evidence_hash,
        governance_hash: plan.governance_hash,
      });
      const startedAt = new Date().toISOString();
      const job = {
        job_id: id,
        plan_id: plan.plan_id,
        status: "RUNNING",
        model: SOL_HEAD.model,
        requested_effort: plan.route.selected_effort,
        submitted_at: startedAt,
        started_at: startedAt,
        cache_hit: false,
        owner_pid: process.pid,
        job_directory: directory,
        ...this.origin,
      };
      atomicJson(jobPath, job);
      const controller = new AbortController();
      const active = {
        controller,
        releaseSlot,
        releaseTaskLock: taskLock.release,
        plan,
        directory,
        cancelled: false,
        timedOut: false,
        timeoutHandle: null,
        beforeExternalStart,
        completion: null,
      };
      this.active.set(id, active);
      active.timeoutHandle = this.timerFunction(() => {
        const current = this.active.get(id);
        if (!current) return;
        current.timedOut = true;
        current.controller.abort();
      }, plan.task.timeoutMs);
      active.timeoutHandle?.unref?.();
      active.completion = this.runActiveJob(id, job, active);
      activeOwnsReleases = true;
      return await active.completion;
    } catch (error) {
      if (!activeOwnsReleases) {
        releaseSlot?.();
        taskLock.release();
      }
      throw error;
    }
  }

  failureHandoff(summary) {
    const safeSummary = safeDiagnosticText(summary);
    return {
      action: "BLOCKED",
      summary: safeSummary,
      evidence_paths: [],
      decision: "",
      requested_evidence: [],
      bounded_delegations: [],
      recommended_effort: "xhigh",
      scientific_uncertainty: false,
      architecture_uncertainty: false,
      residual_risks: [safeSummary],
      recommended_next_action: "Return to the xhigh root for review.",
    };
  }

  async runActiveJob(id, job, active) {
    let response = null;
    let handoff;
    let status;
    let modelCalls = 1;
    let runnerInvoked = false;
    try {
      if (active.beforeExternalStart !== null && active.beforeExternalStart !== undefined) {
        await active.beforeExternalStart();
      }
      runnerInvoked = true;
      response = await this.solRunner(active.plan, {
        jobDirectory: active.directory,
        signal: active.controller.signal,
        budgetController: this.budgetController,
      });
      if (!response?.handoff) throw new Error("Sol head runner returned no handoff");
      handoff = redactDiagnostic(response.handoff);
      const unresolved = new Set(["REQUEST_EVIDENCE", "BLOCKED"]).has(handoff.action) ||
        Boolean(handoff.scientific_uncertainty) ||
        Boolean(handoff.architecture_uncertainty);
      status = unresolved ? "BLOCKED" : "PASS";
    } catch (error) {
      modelCalls =
        !runnerInvoked || error?.headProviderStarted === false ? 0 : 1;
      status = active.cancelled || active.timedOut ? "BLOCKED" : "FAIL";
      const summary = active.timedOut
        ? `Sol head job timed out after ${Math.round(active.plan.task.timeoutMs / 60_000)} minutes.`
        : active.cancelled
          ? "Sol head job cancelled by the xhigh root."
          : safeDiagnosticText(error);
      handoff = this.failureHandoff(summary);
    }
    if (active.timeoutHandle) this.clearTimerFunction(active.timeoutHandle);
    const finishedAt = new Date().toISOString();
    const resultPath = path.join(active.directory, "result.json");
    const usage = response?.usage ?? parseCodexJsonUsage("");
    const actualEffort = response?.actual_effort ?? "UNVERIFIED";
    const result = {
      job_id: id,
      plan_id: active.plan.plan_id,
      status,
      execution_status:
        status === "PASS"
          ? "ACCEPTED"
          : active.cancelled
            ? "CANCELLED"
            : status === "BLOCKED"
              ? "BLOCKED"
              : modelCalls > 0
                ? "PROVIDER_ERROR"
                : "CONTRACT_ERROR",
      evidence_verdict:
        status === "PASS" ? "NOT_APPLICABLE" : "UNRESOLVED",
      summary: handoff.summary,
      head_handoff: handoff,
      model: SOL_HEAD.model,
      requested_effort: active.plan.route.selected_effort,
      actual_effort: actualEffort,
      cache_hit: false,
      finished_at: finishedAt,
      usage,
      api_calls: 0,
      model_calls: modelCalls,
      provider_route: modelCalls > 0 ? [SOL_HEAD.provider] : [],
      provider_usage: {
        sol: {
          provider: SOL_HEAD.provider,
          model: SOL_HEAD.model,
          requested_effort: active.plan.route.selected_effort,
          actual_effort: actualEffort,
          chatgpt_subscription: Boolean(response?.chatgpt_subscription),
          exit_code: Number(response?.exit_code) || 0,
          elapsed_ms: Number(response?.elapsed_ms) || 0,
          usage,
          api_calls: 0,
          model_calls: modelCalls,
        },
      },
      result_path: resultPath,
    };
    try {
      atomicJson(resultPath, result);
      job.status = status;
      job.finished_at = finishedAt;
      atomicJson(path.join(active.directory, "job.json"), job);
      if (active.plan.task.reuseCache && status === "PASS") {
        const cached = { ...result };
        delete cached.job_id;
        delete cached.result_path;
        atomicJson(path.join(this.cacheRoot, `${active.plan.plan_id}.json`), cached);
      }
    } finally {
      this.active.delete(id);
      active.releaseSlot();
      active.releaseTaskLock();
    }
    return headPublicJobState(job, result);
  }

  recoverInterruptedJobs() {
    for (const entry of readdirSync(this.jobsRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = path.join(this.jobsRoot, entry.name);
      const jobPath = path.join(directory, "job.json");
      if (!existsSync(jobPath)) continue;
      let job;
      try {
        job = readJson(jobPath);
      } catch {
        continue;
      }
      if (job.status !== "RUNNING" || processAlive(Number(job.owner_pid))) continue;
      const finishedAt = new Date().toISOString();
      const handoff = this.failureHandoff(
        "Sol head server stopped before the structured handoff was recorded.",
      );
      const resultPath = path.join(directory, "result.json");
      const result = {
        job_id: job.job_id,
        plan_id: job.plan_id,
        status: "BLOCKED",
        summary: handoff.summary,
        head_handoff: handoff,
        model: job.model ?? SOL_HEAD.model,
        requested_effort: job.requested_effort ?? null,
        actual_effort: "UNVERIFIED",
        cache_hit: false,
        finished_at: finishedAt,
        usage: parseCodexJsonUsage(""),
        api_calls: 0,
        model_calls: 0,
        provider_route: [],
        provider_usage: { sol: null },
        result_path: resultPath,
      };
      atomicJson(resultPath, result);
      job.status = "BLOCKED";
      job.finished_at = finishedAt;
      atomicJson(jobPath, job);
    }
  }

  metrics() {
    const metrics = {
      policy: SOL_HEAD.policy,
      model: SOL_HEAD.model,
      jobs: { total: 0, statuses: {}, cache_hits: 0 },
      efforts: Object.fromEntries(
        SOL_HEAD.efforts.map((effort) => [effort, {
          runs: 0,
          model_calls: 0,
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        }]),
      ),
      max_attempts: Object.keys(this.readState().max_attempts).length,
    };
    for (const entry of readdirSync(this.jobsRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = path.join(this.jobsRoot, entry.name);
      const jobPath = path.join(directory, "job.json");
      if (!existsSync(jobPath)) continue;
      let job;
      try {
        job = readJson(jobPath);
      } catch {
        continue;
      }
      metrics.jobs.total += 1;
      metrics.jobs.statuses[job.status] = (metrics.jobs.statuses[job.status] ?? 0) + 1;
      if (job.cache_hit || job.status === "CACHED") metrics.jobs.cache_hits += 1;
      if (job.cache_hit || job.status === "CACHED") continue;
      const resultPath = path.join(directory, "result.json");
      if (!existsSync(resultPath)) continue;
      let result;
      try {
        result = readJson(resultPath);
      } catch {
        continue;
      }
      const effort = job.requested_effort;
      if (!metrics.efforts[effort]) continue;
      const target = metrics.efforts[effort];
      target.runs += 1;
      target.model_calls += Number(result.model_calls) || 0;
      for (const key of [
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
      ]) target[key] += Number(result.usage?.[key]) || 0;
    }
    return metrics;
  }

  status(id) {
    if (!/^SH-[A-Za-z0-9-]+$/.test(String(id ?? ""))) throw new Error("invalid head job_id");
    const directory = path.join(this.jobsRoot, id);
    const jobPath = path.join(directory, "job.json");
    if (!existsSync(jobPath)) throw new Error(`unknown head job_id: ${id}`);
    const job = readJson(jobPath);
    assertOriginOwns(job, this.origin);
    const resultPath = path.join(directory, "result.json");
    return headPublicJobState(job, existsSync(resultPath) ? readJson(resultPath) : null);
  }

  cancel(id) {
    if (!/^SH-[A-Za-z0-9-]+$/.test(String(id ?? ""))) throw new Error("invalid head job_id");
    const jobPath = path.join(this.jobsRoot, id, "job.json");
    if (!existsSync(jobPath)) {
      return { job_id: id, cancelled: false, reason: "head job is not known to this project" };
    }
    assertOriginOwns(readJson(jobPath), this.origin);
    const active = this.active.get(id);
    if (!active) {
      return { job_id: id, cancelled: false, reason: "head job is not active in this server" };
    }
    active.cancelled = true;
    active.controller.abort();
    return { job_id: id, cancelled: true, reason: "Sol head cancellation requested" };
  }

  cancelAll() {
    for (const [id, active] of this.active) {
      active.cancelled = true;
      active.controller.abort();
      console.error(safeDiagnosticText(
        `Cancellation requested for ${id} because the MCP transport closed.`,
      ));
    }
  }
}

export class JobManager {
  constructor({
    storeRoot = defaultStoreRoot(),
    projectId = process.env.DEEPLUNA_PROJECT_ID,
    projectScope = process.env.DEEPLUNA_PROJECT_SCOPE,
    originThreadId = process.env.CODEX_THREAD_ID,
    originContext = null,
    projectSecretFactory = crypto.randomBytes,
    fetchFunction = globalThis.fetch,
    budgetController = null,
    primaryProfile = resolvePrimaryProfile(),
    apiKey = resolvePrimaryApiKey(primaryProfile),
    commandRunner,
    lunaRunner = runFallbackAgent,
    timerFunction = setTimeout,
    clearTimerFunction = clearTimeout,
    retentionDays = Number(process.env.DEEPLUNA_RETENTION_DAYS) || 30,
    cacheMaxBytes = Number(process.env.DEEPLUNA_CACHE_MAX_BYTES) || 256 * 1024 * 1024,
    nowFunction = Date.now,
    circuitCooldownMs = Number(process.env.DEEPLUNA_CIRCUIT_COOLDOWN_MS) || 120_000,
    codexOrchestrationEnabled = resolveCodexOrchestrationEnabled(),
    estimatedLunaCostUsd = 0,
    jobIdFactory = jobId,
  } = {}) {
    this.baseStoreRoot = path.resolve(storeRoot);
    this.storeRoot = this.baseStoreRoot;
    this.projectScope = resolveProjectScope(projectScope);
    this.projectId = resolveProjectId(projectId, process.cwd());
    const projectRoot = path.join(this.baseStoreRoot, "projects", this.projectId);
    this.projectRoot = projectRoot;
    const projectSecret = ensureProjectSecret(projectRoot, projectSecretFactory);
    this.projectSecret = projectSecret;
    this.origin = originContext ?? deriveOriginContext(
      originThreadId ?? `local-${process.pid}-${crypto.randomUUID()}`,
      projectSecret,
    );
    const scoped = projectStorePaths(this.baseStoreRoot, this.projectId, {
      scope: this.projectScope,
      threadScope: this.origin.originThreadHash,
    });
    Object.assign(this, scoped);
    this.statePath = scoped.workerStatePath;
    this.stateLockPath = scoped.workerStateLockPath;
    this.legacyJobsRoot = path.join(scoped.legacyRoot, "jobs");
    this.fetchFunction = fetchFunction;
    this.budgetController = budgetController;
    this.negativeAdmissionCoordinator = createNegativeAdmissionCoordinator(
      this.projectRoot,
      { nowFunction },
    );
    this.primaryProfile = primaryProfile;
    this.apiKey = apiKey;
    this.commandRunner = commandRunner ?? runApprovedCommand;
    this.lunaRunner = lunaRunner;
    this.timerFunction = timerFunction;
    this.clearTimerFunction = clearTimerFunction;
    this.retentionDays = Math.max(1, Number(retentionDays) || 30);
    this.cacheMaxBytes = Math.max(1, Number(cacheMaxBytes) || 256 * 1024 * 1024);
    this.nowFunction = nowFunction;
    this.circuitCooldownMs = Math.max(1_000, Number(circuitCooldownMs) || 120_000);
    this.codexOrchestrationEnabled = Boolean(codexOrchestrationEnabled);
    this.estimatedLunaCostUsd = Math.max(0, Number(estimatedLunaCostUsd) || 0);
    if (typeof jobIdFactory !== "function") {
      throw new TypeError("jobIdFactory must be a function");
    }
    this.jobIdFactory = jobIdFactory;
    this.active = new Map();
    mkdirSync(this.jobsRoot, { recursive: true });
    mkdirSync(this.cacheRoot, { recursive: true });
    mkdirSync(this.lockRoot, { recursive: true });
    if (!existsSync(this.statePath)) this.mutateFailureState(() => {});
    removeStaleLocks(this.lockRoot);
    this.pruneStore();
    this.recoverInterruptedJobs();
  }

  pruneStore() {
    const cutoff = this.nowFunction() - this.retentionDays * 24 * 60 * 60 * 1_000;
    const removed = { jobs: 0, cache_entries: 0, cache_bytes: 0 };
    for (const entry of readdirSync(this.jobsRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = path.join(this.jobsRoot, entry.name);
      const jobPath = path.join(directory, "job.json");
      if (!existsSync(jobPath)) continue;
      try {
        const job = readJson(jobPath);
        if (job.status === "RUNNING") continue;
        const timestamp = Date.parse(job.finished_at ?? job.submitted_at ?? "");
        if (Number.isFinite(timestamp) && timestamp < cutoff) {
          rmSync(directory, { recursive: true, force: true });
          removed.jobs += 1;
        }
      } catch {
        // Retain malformed evidence for manual review rather than deleting it automatically.
      }
    }

    const cacheEntries = [];
    for (const entry of readdirSync(this.cacheRoot, { withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
      const cachePath = path.join(this.cacheRoot, entry.name);
      try {
        const cached = readJson(cachePath);
        const stats = statSync(cachePath);
        const timestamp = Date.parse(cached.finished_at ?? "");
        const age = Number.isFinite(timestamp) ? timestamp : stats.mtimeMs;
        if (age < cutoff) {
          removed.cache_bytes += stats.size;
          removed.cache_entries += 1;
          unlinkSync(cachePath);
          continue;
        }
        cacheEntries.push({ path: cachePath, timestamp: age, size: stats.size });
      } catch {
        // Retain malformed cache evidence for manual inspection.
      }
    }
    let cacheBytes = cacheEntries.reduce((total, entry) => total + entry.size, 0);
    for (const entry of cacheEntries.sort((left, right) => left.timestamp - right.timestamp)) {
      if (cacheBytes <= this.cacheMaxBytes) break;
      unlinkSync(entry.path);
      cacheBytes -= entry.size;
      removed.cache_bytes += entry.size;
      removed.cache_entries += 1;
    }
    return { ...removed, remaining_cache_bytes: cacheBytes };
  }

  metrics() {
    const metrics = {
      process_name: this.primaryProfile.displayName,
      version: VERSION,
      cumulative_budget_safe: false,
      daemon_active: false,
      active_primary_profile: this.primaryProfile.id,
      jobs: { total: 0, statuses: {}, cache_hits: 0 },
      cache: {
        entries: 0,
        bytes: 0,
        retention_days: this.retentionDays,
        max_bytes: this.cacheMaxBytes,
      },
      providers: {
        primary: {
          profile_id: this.primaryProfile.id,
          provider: this.primaryProfile.provider,
          route: this.primaryProfile.route,
          model: this.primaryProfile.models.FLASH,
          service_tier: this.primaryProfile.serviceTier,
          runs: 0,
          api_calls: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
          prompt_cache_hit_tokens: 0,
          prompt_cache_miss_tokens: 0,
        },
        luna: {
          runs: 0,
          elapsed_ms: 0,
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        },
        glm: {
          runs: 0,
          elapsed_ms: 0,
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        },
        local: {
          runs: 0,
          commands: 0,
          writes: 0,
          failures: 0,
        },
      },
    };
    for (const entry of readdirSync(this.cacheRoot, { withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
      metrics.cache.entries += 1;
      try {
        metrics.cache.bytes += statSync(path.join(this.cacheRoot, entry.name)).size;
      } catch {
        // Ignore entries that disappear during a concurrent prune.
      }
    }
    for (const entry of readdirSync(this.jobsRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = path.join(this.jobsRoot, entry.name);
      const jobPath = path.join(directory, "job.json");
      if (!existsSync(jobPath)) continue;
      let job;
      try {
        job = readJson(jobPath);
      } catch {
        continue;
      }
      metrics.jobs.total += 1;
      metrics.jobs.statuses[job.status] = (metrics.jobs.statuses[job.status] ?? 0) + 1;
      if (job.cache_hit || job.status === "CACHED") metrics.jobs.cache_hits += 1;
      if (job.cache_hit || job.status === "CACHED") continue;
      const resultPath = path.join(directory, "result.json");
      if (!existsSync(resultPath)) continue;
      let providerUsage;
      try {
        providerUsage = readJson(resultPath).provider_usage;
      } catch {
        continue;
      }
      const primary = providerUsage?.primary ?? providerUsage?.deepseek;
      if ((Number(primary?.api_calls) || 0) > 0) metrics.providers.primary.runs += 1;
      metrics.providers.primary.api_calls += Number(primary?.api_calls) || 0;
      for (const key of [
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
      ]) {
        metrics.providers.primary[key] += Number(primary?.usage?.[key]) || 0;
      }
      const fallbackUsage = {
        luna: providerUsage?.luna,
        glm: providerUsage?.glm,
      };
      for (const [provider, usage] of Object.entries(fallbackUsage)) {
        if (!usage) continue;
        metrics.providers[provider].runs += 1;
        metrics.providers[provider].elapsed_ms += Number(usage.elapsed_ms) || 0;
        for (const key of [
          "input_tokens",
          "cached_input_tokens",
          "output_tokens",
          "reasoning_output_tokens",
          "total_tokens",
        ]) {
          metrics.providers[provider][key] += Number(usage.usage?.[key]) || 0;
        }
      }

      const localUsage = providerUsage?.local;
      if (!localUsage) continue;
      metrics.providers.local.runs += Number(localUsage.runs) || 0;
      metrics.providers.local.commands += Number(localUsage.commands) || 0;
      metrics.providers.local.writes += Number(localUsage.writes) || 0;
      metrics.providers.local.failures += localUsage.status === "FAIL" || localUsage.status === "BLOCKED"
        ? 1
        : 0;
    }
    return metrics;
  }

  defaultFailureState() {
    const fallbackRouteState = {
      consecutive_failures: 0,
      last_status: null,
      last_failure_class: null,
      updated_at: null,
      open_until: null,
    };
    return {
      version: 4,
      active_primary_profile: this.primaryProfile.id,
      primary_profiles: {
        [this.primaryProfile.id]: this.defaultPrimaryFailureState(),
      },
      luna: { ...fallbackRouteState },
      glm: { ...fallbackRouteState },
      reset_reason: null,
    };
  }

  defaultPrimaryFailureState() {
    return {
      consecutive_failures: 0,
      last_status: null,
      last_provider_status: null,
      last_provider_failure_class: null,
      updated_at: null,
      open_until: null,
      tasks: {},
    };
  }

  primaryFailureState(state, profileId = this.primaryProfile.id) {
    state.primary_profiles ??= {};
    state.primary_profiles[profileId] ??= this.defaultPrimaryFailureState();
    state.active_primary_profile = this.primaryProfile.id;
    return state.primary_profiles[profileId];
  }

  readFailureState() {
    try {
      const raw = readJson(this.statePath);
      const state = this.defaultFailureState();
      if (raw.version !== 4 || !raw.primary_profiles) return state;
      state.primary_profiles = {};
      for (const [profileId, profileState] of Object.entries(raw.primary_profiles)) {
        state.primary_profiles[profileId] = {
          ...this.defaultPrimaryFailureState(),
          ...profileState,
          tasks:
            profileState?.tasks && typeof profileState.tasks === "object"
              ? profileState.tasks
              : {},
        };
      }
      state.luna = {
        consecutive_failures: Number(raw.luna?.consecutive_failures) || 0,
        last_status: raw.luna?.last_status ?? null,
        last_failure_class: raw.luna?.last_failure_class ?? null,
        updated_at: raw.luna?.updated_at ?? null,
        open_until: raw.luna?.open_until ?? this.legacyFallbackOpenUntil(raw.luna),
      };
      state.glm = {
        consecutive_failures: Number(raw.glm?.consecutive_failures) || 0,
        last_status: raw.glm?.last_status ?? null,
        last_failure_class: raw.glm?.last_failure_class ?? null,
        updated_at: raw.glm?.updated_at ?? null,
        open_until: raw.glm?.open_until ?? this.legacyFallbackOpenUntil(raw.glm),
      };
      state.reset_reason = raw.reset_reason ?? null;
      this.primaryFailureState(state);
      return state;
    } catch {
      return this.defaultFailureState();
    }
  }

  legacyFallbackOpenUntil(routeState) {
    if (Number(routeState?.consecutive_failures ?? 0) < 2) return null;
    const updatedAtMs = Date.parse(routeState?.updated_at ?? "");
    if (!Number.isFinite(updatedAtMs)) return new Date(8.64e15).toISOString();
    return new Date(updatedAtMs + this.circuitCooldownMs).toISOString();
  }

  fallbackCircuitIsOpen(routeState, nowMs = this.nowFunction()) {
    if (Number(routeState?.consecutive_failures ?? 0) < 2) return false;
    const openUntilMs = Date.parse(routeState?.open_until ?? "");
    return Number.isFinite(openUntilMs) && openUntilMs > nowMs;
  }

  mutateFailureState(mutator) {
    const release = acquireStateLock(this.stateLockPath);
    try {
      const state = this.readFailureState();
      mutator(state);
      atomicJson(this.statePath, state);
      return state;
    } finally {
      release();
    }
  }

  recordOutcome(status) {
    return this.recordProviderOutcome("primary", "legacy-record-outcome", {
      status,
      failureClass: status === "PASS" || status === "CACHED"
        ? "SUCCESS"
        : "NONRETRYABLE_PROVIDER",
    });
  }

  recordProviderOutcome(provider, fingerprint, { status, failureClass = null }) {
    return this.mutateFailureState((state) => {
      const nowMs = this.nowFunction();
      const now = new Date(nowMs).toISOString();
      if (provider === "primary") {
        const primary = this.primaryFailureState(state);
        const providerFailure = new Set([
          "TRANSIENT_READ_ONLY",
          "NONRETRYABLE_PROVIDER",
          "PROVIDER_FAILURE",
        ]).has(failureClass);
        primary.last_status = status;
        primary.updated_at = now;

        if (failureClass === "SUCCESS") {
          primary.consecutive_failures = 0;
          primary.last_provider_status = "AVAILABLE";
          primary.last_provider_failure_class = null;
          primary.open_until = null;
          delete primary.tasks[fingerprint];
          return;
        }

        const previous = primary.tasks[fingerprint] ?? {
          consecutive_failures: 0,
          deepseek_attempts: 0,
        };
        const deepseekAttempts = Number(previous.deepseek_attempts) + 1;
        primary.tasks[fingerprint] = {
          ...previous,
          consecutive_failures: Number(previous.consecutive_failures) + 1,
          deepseek_attempts: deepseekAttempts,
          failure_class: failureClass,
          fallback_eligible:
            failureClass === "NONRETRYABLE_TASK" ||
            failureClass === "NONRETRYABLE_PROVIDER" ||
            failureClass === "PROVIDER_FAILURE" ||
            (failureClass === "TRANSIENT_READ_ONLY" && deepseekAttempts >= 2),
          last_status: status,
          updated_at: now,
        };

        if (providerFailure) {
          primary.consecutive_failures = Number(primary.consecutive_failures) + 1;
          primary.last_provider_status = "FAIL";
          primary.last_provider_failure_class = failureClass;
          if (primary.consecutive_failures >= 2) {
            primary.open_until = new Date(nowMs + this.circuitCooldownMs).toISOString();
          }
        } else {
          // A structured task result proves the provider responded even when the task failed.
          primary.consecutive_failures = 0;
          primary.last_provider_status = "AVAILABLE";
          primary.last_provider_failure_class = null;
          primary.open_until = null;
        }
      } else if (provider === "luna" || provider === "glm") {
        const key = fallbackStateKey(provider);
        state[key].last_status = status;
        state[key].last_failure_class = failureClass;
        state[key].updated_at = now;
        if (failureClass === "SUCCESS") {
          state[key].consecutive_failures = 0;
          state[key].last_failure_class = null;
          state[key].open_until = null;
          return;
        }
        if (
          new Set([
            "TRANSIENT_READ_ONLY",
            "NONRETRYABLE_PROVIDER",
            "PROVIDER_FAILURE",
          ]).has(failureClass)
        ) {
          state[key].consecutive_failures =
            Number(state[key].consecutive_failures) + 1;
          if (state[key].consecutive_failures >= 2) {
            state[key].open_until =
              new Date(nowMs + this.circuitCooldownMs).toISOString();
          }
        }
      } else {
        throw new Error(`unknown provider outcome: ${provider}`);
      }
    });
  }

  resetProviderCircuit(provider, reason) {
    const normalizedProvider = String(provider ?? "").toLowerCase();
    if (!["primary", "luna", "glm"].includes(normalizedProvider)) {
      throw new Error("provider circuit reset requires primary, luna, or glm");
    }
    const reviewedReason = String(reason ?? "").trim();
    if (reviewedReason.length < 12) {
      throw new Error("failure-stop reset requires a reviewed root-cause reason");
    }
    return this.mutateFailureState((state) => {
      const updatedAt = new Date(this.nowFunction()).toISOString();
      if (normalizedProvider === "primary") {
        state.primary_profiles[this.primaryProfile.id] = this.defaultPrimaryFailureState();
        const primary = this.primaryFailureState(state);
        primary.last_status = "RESET_AFTER_REVIEW";
        primary.updated_at = updatedAt;
      } else {
        state[normalizedProvider] = {
          consecutive_failures: 0,
          last_status: "RESET_AFTER_REVIEW",
          last_failure_class: null,
          updated_at: updatedAt,
          open_until: null,
        };
      }
      state.reset_reason = `${normalizedProvider}: ${reviewedReason}`;
    });
  }

  resetFailureStop(reason) {
    return this.resetProviderCircuit("luna", reason);
  }

  recoverInterruptedJobs() {
    for (const entry of readdirSync(this.jobsRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = path.join(this.jobsRoot, entry.name);
      const jobPath = path.join(directory, "job.json");
      if (!existsSync(jobPath)) continue;
      let job;
      try {
        job = readJson(jobPath);
      } catch {
        continue;
      }
      if (job.status !== "RUNNING") continue;
      if (processAlive(Number(job.owner_pid))) continue;
      const finishedAt = new Date().toISOString();
      const resultPath = path.join(directory, "result.json");
      const normalized = redactDiagnostic({
        status: "BLOCKED",
        execution_status: "BLOCKED",
        evidence_verdict: "UNRESOLVED",
        summary: "MCP server stopped before the direct DeepSeek handoff was recorded.",
        files_inspected: [],
        files_changed: [],
        commands_run: [],
        tests: [],
        positive_findings: [],
        negative_findings: [],
        scientific_uncertainty: false,
        architecture_uncertainty: false,
        scope_deviation: false,
        residual_risks: ["Inspect partial API audit logs before deciding whether to resubmit."],
        recommended_next_action: "Return to Sol for interruption review.",
      }, [this.apiKey]);
      const result = {
        job_id: job.job_id,
        ...normalized,
        coverage_status: job.coverage_status ?? "NOT_REQUESTED",
        cache_hit: false,
        finished_at: finishedAt,
        usage: emptyUsage(),
        api_calls: 0,
        raw_output_path: path.join(directory, "deepseek-api.jsonl"),
        result_path: resultPath,
        sol_handoff: compactSolHandoff(normalized, { resultPath }),
      };
      atomicJson(resultPath, result);
      job.status = "BLOCKED";
      job.execution_status = "BLOCKED";
      job.evidence_verdict = "UNRESOLVED";
      job.finished_at = finishedAt;
      atomicJson(jobPath, job);
    }
  }

  canUseLuna(task, result, attempts = 0, fallbackRoute = "LUNA") {
    return this.codexOrchestrationEnabled && isFallbackEligible(
      result,
      task.routeConstraints,
      attempts,
      this.estimatedLunaCostUsd,
      fallbackRoute,
    );
  }

  selectFallbackRoute(task, result, attempts = 0, failureState = this.readFailureState()) {
    const allowedFallbackRoutes = task.routeConstraints?.allowedRoutes
      ?.filter((route) => new Set(["LUNA", "GLM"]).has(String(route).toUpperCase()))
      .map((route) => normalizeFallbackRoute(route)) ?? [];
    for (const fallbackRoute of allowedFallbackRoutes) {
      const key = fallbackStateKey(fallbackRoute);
      if (
        this.canUseLuna(task, result, attempts, fallbackRoute) &&
        !this.fallbackCircuitIsOpen(failureState?.[key], this.nowFunction())
      ) {
        return fallbackRoute;
      }
    }
    return null;
  }

  redact(value) {
    return redactDiagnostic(value, [this.apiKey]);
  }

  safeSummary(value, maximum = 2_000) {
    return safeDiagnosticText(value, [this.apiKey], maximum);
  }

  jobEnvelope(id, task, cacheKey, extra = {}) {
    return {
      schema_version: 1,
      project_id: this.projectId,
      workspace_instance_id: task.workspaceInstanceId,
      ...this.origin,
      caller_task_id: task.taskId,
      job_id: id,
      fast_only: task.fastOnly === true,
      attempt_id: task.attemptId ?? null,
      attempt_ordinal: task.attemptOrdinal ?? null,
      contract_hash: task.contractHash,
      input_manifest_hash: task.inputManifestHash,
      coverage_hash: task.coverageHash,
      frozen_artifact_policy_version: task.frozenArtifactPolicyVersion ?? null,
      frozen_artifacts: frozenArtifactDescriptors(task.frozenArtifacts),
      frozen_artifact_payload_identity:
        task.frozenArtifactPayloadIdentity ?? frozenArtifactPayloadIdentity([]),
      route: task.attemptRoute ?? null,
      model: task.attemptModel ?? null,
      route_constraints: task.routeConstraints,
      cache_key: cacheKey,
      bridge_release: VERSION,
      protocols: PROTOCOLS,
      protocol_versions: PROTOCOLS,
      ...extra,
    };
  }

  withAttemptIdentity(id, task, ordinal, route, model) {
    return Object.freeze({
      ...task,
      attemptId: deriveAttemptId(id, ordinal, route, this.projectSecret),
      attemptOrdinal: ordinal,
      attemptRoute: route,
      attemptModel: model,
    });
  }

  persistAttemptEnvelope(directory, id, task, cacheKey, provider) {
    if (!task.attemptId || !Number.isInteger(task.attemptOrdinal) || !task.attemptRoute) {
      throw new Error("executable attempt identity is incomplete");
    }
    const routeSlug = String(task.attemptRoute).toLowerCase().replace(/[^a-z0-9-]+/g, "-");
    const attemptDirectory = path.join(
      directory,
      "attempts",
      `${String(task.attemptOrdinal).padStart(2, "0")}-${routeSlug}`,
    );
    mkdirSync(attemptDirectory, { recursive: true });
    atomicJson(
      path.join(attemptDirectory, "envelope.json"),
      this.jobEnvelope(id, task, cacheKey, { provider }),
    );
  }

  persistJobInputs(
    directory,
    id,
    task,
    cacheKey,
    { requestExtra = {}, envelopeExtra = {}, receipts = [] } = {},
  ) {
    atomicJson(path.join(directory, "request.json"), {
      ...durableTaskAuditRecord(task),
      ...this.origin,
      timeoutMs: task.timeoutMs,
      cache_key: cacheKey,
      ...requestExtra,
    });
    atomicJson(path.join(directory, "contract.json"), contractRecord(task));
    atomicJson(
      path.join(directory, "envelope.json"),
      this.jobEnvelope(id, task, cacheKey, envelopeExtra),
    );
    if (task.inputManifest) {
      atomicJson(path.join(directory, "input-manifest.json"), task.inputManifest);
      atomicJson(path.join(directory, "coverage-spec.json"), {
        schema_version: 1,
        coverage_spec: task.coverageSpec,
        coverage_hash: task.coverageHash,
      });
      const receiptText = receipts.length > 0
        ? `${receipts.map((receipt) => JSON.stringify(receipt)).join("\n")}\n`
        : "";
      writeFileSync(path.join(directory, "evidence-receipts.jsonl"), receiptText, "utf8");
    }
  }

  createImmediateResult(id, task, cacheKey, candidate, summary, fallbackReason = null) {
    const safeSummary = this.safeSummary(summary);
    const normalized = withResultSemantics({ ...candidate, summary: safeSummary });
    const directory = path.join(this.jobsRoot, id);
    mkdirSync(directory, { recursive: true });
    const now = new Date().toISOString();
    const result = {
      job_id: id,
      ...normalized,
      coverage_status: task.coverageStatus,
      cache_hit: false,
      finished_at: now,
      usage: emptyUsage(),
      api_calls: 0,
      provider_route: [],
      fallback: {
        used: false,
        reason: fallbackReason,
        attempt: 0,
        primary_error: safeSummary,
      },
      provider_usage: { primary: null, luna: null, glm: null },
    };
    const job = {
      job_id: id,
      task_id: task.taskId,
      status: normalized.status,
      execution_status: normalized.execution_status,
      evidence_verdict: normalized.evidence_verdict,
      coverage_status: task.coverageStatus,
      mode: task.mode,
      tier: task.tier,
      model: task.model,
      provider: null,
      submitted_at: now,
      finished_at: now,
      cache_hit: false,
      cache_key: cacheKey,
      job_directory: directory,
      ...this.origin,
    };
    this.persistJobInputs(directory, id, task, cacheKey);
    atomicJson(path.join(directory, "result.json"), result);
    atomicJson(path.join(directory, "job.json"), job);
    return publicJobState(job, result);
  }

  cachePath(cacheKey) {
    return path.join(this.cacheRoot, `${cacheKey}.json`);
  }

  validateAcceptedCache(cached, task, cacheKey) {
    const executionStatus = cached?.execution_status ??
      (new Set(["PASS", "CACHED"]).has(cached?.status) ? "ACCEPTED" : null);
    if (executionStatus !== "ACCEPTED") throw new Error("cache result is not accepted");
    if (cached.project_id !== this.projectId) throw new Error("cache project identity is invalid");
    if (cached.cache_key !== cacheKey) throw new Error("cache key identity is invalid");
    if (stableJson(cached.protocols) !== stableJson(PROTOCOLS)) {
      throw new Error("cache protocol identity is stale");
    }
    if (stableJson(cached.route_constraints ?? null) !== stableJson(task.routeConstraints ?? null)) {
      throw new Error("cache route constraints are incompatible");
    }
    if (cached.contract_hash !== task.contractHash) {
      throw new Error("cache contract identity is stale");
    }
    if (cached.input_manifest_hash !== task.inputManifestHash) {
      throw new Error("cache input manifest identity is stale");
    }
    if (cached.coverage_hash !== task.coverageHash) {
      throw new Error("cache coverage identity is stale");
    }
    return {
      executionStatus,
      evidenceVerdict: cached.evidence_verdict ?? "NOT_APPLICABLE",
    };
  }

  rematerializeCachedEvidence(id, task, cached) {
    if ((task.requiredReads ?? []).length === 0) return { cached, receipts: [] };
    if (!Array.isArray(cached.evidence_receipts)) {
      throw new Error("cache evidence receipts are missing");
    }
    const evidenceIdMap = new Map();
    const receipts = cached.evidence_receipts.map((source) => {
      const expectedSource = createReadReceipt({
        manifest: task.inputManifest,
        jobId: source.job_id,
        workspaceInstanceId: source.workspace_instance_id,
        relativePath: source.relative_path,
        start: source.start,
        end: source.end,
      });
      if (stableJson(expectedSource) !== stableJson(source)) {
        throw new Error(`cache evidence receipt is tampered: ${source.evidence_id ?? "unknown"}`);
      }
      const materialized = createReadReceipt({
        manifest: task.inputManifest,
        jobId: id,
        workspaceInstanceId: task.workspaceInstanceId,
        relativePath: source.relative_path,
        start: source.start,
        end: source.end,
      });
      evidenceIdMap.set(source.evidence_id, materialized.evidence_id);
      return materialized;
    });
    const citations = Array.isArray(cached.citations)
      ? cached.citations.map((citation) => ({
          ...citation,
          evidence_id: evidenceIdMap.get(citation.evidence_id) ?? citation.evidence_id,
        }))
      : [];
    const validation = validateEvidenceResult({
      handoff: { ...cached, citations },
      manifest: task.inputManifest,
      receipts,
      requiredReads: task.requiredReads,
      coverageSpec: task.coverageSpec,
      jobId: id,
      workspaceInstanceId: task.workspaceInstanceId,
      resolvePath: (relative) => path.resolve(task.workspace, relative),
    });
    if (validation.coverage_status !== "COMPLETE") {
      throw new Error(`cache evidence is incomplete: ${validation.errors.join("; ")}`);
    }
    return {
      cached: {
        ...cached,
        execution_status: validation.execution_status,
        evidence_verdict: validation.evidence_verdict,
        coverage_status: validation.coverage_status,
        files_inspected: [...validation.files_inspected],
        citations: [...validation.citations],
        evidence_errors: [...validation.errors],
        evidence_receipts: receipts,
      },
      receipts,
    };
  }

  materializeAcceptedCache(id, task, cached, cacheKey, { coalesced = false } = {}) {
    const semantics = this.validateAcceptedCache(cached, task, cacheKey);
    const materializedEvidence = this.rematerializeCachedEvidence(id, task, cached);
    cached = materializedEvidence.cached;
    const directory = path.join(this.jobsRoot, id);
    mkdirSync(directory, { recursive: true });
    const now = new Date().toISOString();
    const result = {
      ...cached,
      job_id: id,
      status: "CACHED",
      execution_status: semantics.executionStatus,
      evidence_verdict: semantics.evidenceVerdict,
      cache_hit: true,
      finished_at: now,
    };
    for (const field of [
      "source_cache_path",
      "source_job_id",
      "producer_job_id",
      "job_directory",
      "result_path",
      "raw_output_path",
      "sol_handoff",
    ]) delete result[field];
    const job = {
      job_id: id,
      task_id: task.taskId,
      status: "CACHED",
      execution_status: semantics.executionStatus,
      evidence_verdict: semantics.evidenceVerdict,
      coverage_status: result.coverage_status ?? task.coverageStatus,
      mode: task.mode,
      tier: task.tier,
      model: task.model,
      provider: result.provider ?? task.primaryRoute,
      submitted_at: now,
      finished_at: now,
      cache_hit: true,
      coalesced,
      cache_key: cacheKey,
      job_directory: directory,
      ...this.origin,
    };
    this.persistJobInputs(directory, id, task, cacheKey, {
      receipts: materializedEvidence.receipts,
    });
    atomicJson(path.join(directory, "result.json"), result);
    atomicJson(path.join(directory, "job.json"), job);
    return publicJobState(job, result);
  }

  createCacheWaiter(id, task, cacheKey) {
    const directory = path.join(this.jobsRoot, id);
    mkdirSync(directory, { recursive: true });
    const now = new Date().toISOString();
    const job = {
      job_id: id,
      task_id: task.taskId,
      status: "RUNNING",
      mode: task.mode,
      tier: task.tier,
      model: task.model,
      provider: task.primaryRoute,
      coverage_status: task.coverageStatus,
      submitted_at: now,
      started_at: now,
      cache_hit: false,
      coalesced: true,
      waiting_for_cache: true,
      cache_key: cacheKey,
      job_directory: directory,
      ...this.origin,
    };
    this.persistJobInputs(directory, id, task, cacheKey, {
      envelopeExtra: { coalesced: true },
    });
    atomicJson(path.join(directory, "job.json"), job);
    return publicJobState(job);
  }

  completeCacheWaiter(job, directory) {
    const cacheKey = job.cache_key;
    const cachePath = this.cachePath(cacheKey);
    const requestPath = path.join(directory, "request.json");
    if (existsSync(cachePath)) {
      return this.materializeAcceptedCache(
        job.job_id,
        readJson(requestPath),
        readJson(cachePath),
        cacheKey,
        { coalesced: true },
      );
    }
    const lockPath = path.join(this.lockRoot, `task-${cacheKey}.lock`);
    if (existsSync(lockPath)) return publicJobState(job);
    const finishedAt = new Date().toISOString();
    const result = {
      job_id: job.job_id,
      status: "FAIL",
      execution_status: "INCOMPLETE",
      evidence_verdict: "UNRESOLVED",
      summary: "The single-flight producer exited without publishing an accepted cache result.",
      cache_hit: false,
      finished_at: finishedAt,
      usage: emptyUsage(),
      api_calls: 0,
      provider_route: [],
      fallback: null,
      provider_usage: { primary: null, luna: null, glm: null },
    };
    job.status = "FAIL";
    job.execution_status = "INCOMPLETE";
    job.evidence_verdict = "UNRESOLVED";
    job.finished_at = finishedAt;
    delete job.waiting_for_cache;
    atomicJson(path.join(directory, "result.json"), result);
    atomicJson(path.join(directory, "job.json"), job);
    return publicJobState(job, result);
  }

  async submit(raw, mode) {
    const validated = validateSubmission(raw, mode, this.primaryProfile, {
      codexOrchestrationEnabled: this.codexOrchestrationEnabled,
    });
    const id = this.jobIdFactory();
    if (!/^(?:DS|DJ)-[A-Za-z0-9-]+$/.test(id)) {
      throw new Error("jobIdFactory returned an invalid DeepLuna job identity");
    }
    const directory = path.join(this.jobsRoot, id);
    const localRoute = shouldUseLocalRoute(validated);
    let localCapture = null;
    if (localRoute) {
      mkdirSync(directory, { recursive: false });
      if (!validated.localExactWrite) {
        try {
          localCapture = captureLocalDependencies(
            validated,
            path.join(directory, "local-snapshot"),
          );
        } catch (error) {
          rmSync(directory, { recursive: true, force: true });
          throw error;
        }
      }
    }
    const workspaceInstanceId = deriveWorkspaceInstanceId(
      validated.workspace,
      this.projectSecret,
    );
    const projectHmac = opaqueProjectIdentity(
      this.projectSecret,
      "DEEPLUNA_PROJECT_HMAC_V1",
      this.projectId,
    );
    const canaryRunSource =
      validated.taskId === "UNASSIGNED" ? id : validated.taskId;
    const canaryRunId =
      `CR-${opaqueProjectIdentity(
        this.projectSecret,
        "DEEPLUNA_CANARY_RUN_V1",
        canaryRunSource,
      ).slice(0, 32)}`;
    const contractCandidate = {
      ...validated,
      localDependencyIdentity: localCapture?.identity ?? [],
      projectId: this.projectId,
      jobId: id,
      workspaceInstanceId,
      projectHmac,
      canaryRunId,
    };
    const contractHash = buildContractHash(contractCandidate);
    const inputManifest = validated.requiredReads.length > 0
      ? buildTextEvidenceManifest({
          requiredReads: validated.requiredReads,
          resolvePath: (relative) =>
            resolveRequiredReadPath(validated, relative).fullPath,
        })
      : null;
    let task = Object.freeze({
      ...contractCandidate,
      contractHash,
      inputManifest,
      inputManifestHash: inputManifest?.manifest_hash ?? canonicalHash(null),
      attemptId: null,
      attemptOrdinal: null,
      attemptRoute: null,
      attemptModel: null,
    });
    const taskFingerprint = buildTaskFingerprint(task, this.origin);
    let cacheKey = null;
    if (task.reuseCache) {
      try {
        const fingerprint = localCapture
          ? localCapture.fingerprint
          : await fingerprintAllowedPaths(task.workspace, task.allowedPaths);
        cacheKey = buildCacheKey(task, fingerprint);
        const cachedPath = this.cachePath(cacheKey);
        if (existsSync(cachedPath)) {
          const materialized = this.materializeAcceptedCache(
            id,
            task,
            readJson(cachedPath),
            cacheKey,
          );
          if (localCapture?.snapshotRoot) {
            rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
          }
          return materialized;
        }
      } catch (error) {
        if (task.requireCache) {
          if (localCapture?.snapshotRoot) {
            rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
          }
          return this.createImmediateResult(
            id,
            task,
            null,
            { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
            `require_cache fingerprint or cache validation failed: ${
              error?.message ?? String(error)
            }`,
            "require-cache-invalid",
          );
        }
        cacheKey = null;
        console.error(this.safeSummary(
          `DeepSeek local cache disabled for this job: ${error?.message ?? String(error)}`,
        ));
      }
    }
    if (task.requireCache) {
      if (localCapture?.snapshotRoot) {
        rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
      }
      return this.createImmediateResult(
        id,
        task,
        cacheKey,
        { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
        "require_cache did not find a valid exact accepted cache entry.",
        "require-cache-miss",
      );
    }

    let startProvider = "deepseek";
    let startReason = null;
    let startFallbackRoute = null;
    const failureState = this.readFailureState();
    if (localRoute) {
      if (
        task.localExactWrite !== true &&
        (!Array.isArray(task.commandsTests) || task.commandsTests.length === 0)
      ) {
        if (localCapture?.snapshotRoot) {
          rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
        }
        return this.createImmediateResult(
          id,
          task,
          cacheKey,
          { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
          "The LOCAL route is allowed but no executable commands_tests were provided.",
          "local-route-missing-commands_tests",
        );
      }
      startProvider = "local";
    }

    if (startProvider !== "local") {
      try {
        requireBudgetController(this.budgetController);
      } catch (error) {
        if (localCapture?.snapshotRoot) {
          rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
        }
        return this.createImmediateResult(
          id,
          task,
          cacheKey,
          { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
          error,
          "cumulative-budget-controller-unavailable",
        );
      }
    }

    if (startProvider === "deepseek") {
      const primaryRoute = primaryRoutePolicyKey(task);
      const primaryFailure = this.primaryFailureState(failureState);
      const taskFailure = primaryFailure.tasks[taskFingerprint];
      const providerCircuitOpen =
        this.fallbackCircuitIsOpen(primaryFailure, this.nowFunction());
      if (!task.routeConstraints.allowedRoutes.includes(primaryRoute)) {
        const unavailable = withResultSemantics({
          execution_status: "PROVIDER_ERROR",
          evidence_verdict: "UNRESOLVED",
        });
        const route = this.selectFallbackRoute(task, unavailable, 0, failureState);
        if (route) {
          startProvider = fallbackRouteProviderSlot(route).provider;
          startFallbackRoute = route;
          startReason = "primary-route-not-authorized";
        } else {
          return this.createImmediateResult(
            id,
            task,
            cacheKey,
            { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
            `The ${primaryRoute} route is excluded and no executable fallback route is authorized.`,
            "primary-route-not-authorized",
          );
        }
      }
      if (taskFailure) {
        const attempts = Number(taskFailure.deepseek_attempts) || 1;
        const providerFailure = new Set([
          "TRANSIENT_READ_ONLY",
          "NONRETRYABLE_PROVIDER",
          "PROVIDER_FAILURE",
        ]).has(taskFailure.failure_class);
        const candidate = providerFailure
          ? { execution_status: "PROVIDER_ERROR", evidence_verdict: "UNRESOLVED" }
          : taskFailure.failure_class === "STOP_FOR_SOL"
            ? { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" }
            : { execution_status: "INCOMPLETE", evidence_verdict: "UNRESOLVED" };
        const summary = taskFailure.failure_class === "STOP_FOR_SOL"
          ? "This task requires Sol review before any provider resubmission."
          : providerFailure
            ? "The prior primary-provider attempt did not produce an accepted result."
            : "The prior worker result was incomplete and is not eligible for model fallback.";
        const fallbackRoute = this.selectFallbackRoute(
          task,
          withResultSemantics(candidate),
          attempts,
          failureState,
        );
        if (fallbackRoute) {
          startProvider = fallbackRouteProviderSlot(fallbackRoute).provider;
          startFallbackRoute = fallbackRoute;
          startReason = taskFailure.failure_class === "TRANSIENT_READ_ONLY"
            ? "previous-transient-primary-retry-exhausted"
            : "previous-primary-provider-failure";
        } else {
          return this.createImmediateResult(
            id,
            task,
            cacheKey,
            candidate,
            summary,
            "prior-result-not-fallback-eligible",
          );
        }
      } else if (providerCircuitOpen) {
        const candidate = withResultSemantics({
          execution_status: "PROVIDER_ERROR",
          evidence_verdict: "UNRESOLVED",
        });
        const fallbackRoute = this.selectFallbackRoute(task, candidate, 0, failureState);
        if (!fallbackRoute) {
          return this.createImmediateResult(
            id,
            task,
            cacheKey,
            candidate,
            "The primary provider circuit is open.",
            "primary-circuit-open-not-fallback-eligible",
          );
        }
        startProvider = fallbackRouteProviderSlot(fallbackRoute).provider;
        startFallbackRoute = fallbackRoute;
        startReason = "primary-circuit-open";
      } else if (!String(this.apiKey ?? "").trim()) {
        const candidate = withResultSemantics({
          execution_status: "PROVIDER_ERROR",
          evidence_verdict: "UNRESOLVED",
        });
        const fallbackRoute = this.selectFallbackRoute(task, candidate, 0, failureState);
        if (!fallbackRoute) {
          const fallbackOpen = (task.routeConstraints?.allowedRoutes ?? [])
            .filter((route) => new Set(["LUNA", "GLM"]).has(String(route).toUpperCase()))
            .map((route) => normalizeFallbackRoute(route))
            .filter((route) => this.canUseLuna(task, candidate, 0, route))
            .find((route) =>
              this.fallbackCircuitIsOpen(failureState[fallbackStateKey(route)], this.nowFunction())
            );
          if (fallbackOpen) {
            return this.createImmediateResult(
              id,
              task,
              cacheKey,
              { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
              `${fallbackOpen} failures stopped; requires Sol review before retry.`,
              `${fallbackOpen.toLowerCase()}-circuit-open`,
            );
          }
          return this.createImmediateResult(
            id,
            task,
            cacheKey,
            candidate,
            "The primary provider credential is unavailable.",
            "primary-credential-unavailable-not-fallback-eligible",
          );
        }
        startProvider = fallbackRouteProviderSlot(fallbackRoute).provider;
        startFallbackRoute = fallbackRoute;
        startReason = "primary-credential-unavailable";
      }
      if (startFallbackRoute) {
        const fallbackState = failureState[fallbackStateKey(startFallbackRoute)];
        if (this.fallbackCircuitIsOpen(fallbackState, this.nowFunction())) {
          return this.createImmediateResult(
            id,
            task,
            cacheKey,
            { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
            `${fallbackProviderLabel(startProvider)} failures stopped; requires Sol review before retry.`,
            `${fallbackRouteFromProvider(startProvider).toLowerCase()}-circuit-open`,
          );
        }
      }
      if (task.routeConstraints.privacyClass === "LOCAL_ONLY") {
        return this.createImmediateResult(
          id,
          task,
          cacheKey,
          { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" },
          "LOCAL route is missing from allowed execution paths.",
          "local-only-cache-miss",
        );
      }
    }

    let taskLock = null;
    if (cacheKey) {
      taskLock = acquireTaskLock(this.lockRoot, cacheKey, id);
      if (!taskLock.acquired) {
        if (localCapture?.snapshotRoot) {
          rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
        }
        return this.createCacheWaiter(id, task, cacheKey);
      }
    }

    let releaseSlot = () => {};
    try {
      if (mode === "WRITE" && startProvider === "local") {
        releaseSlot = acquireSlot(this.lockRoot, "WRITE");
      } else if (mode === "WRITE") {
        releaseSlot = acquireProviderSlot(this.lockRoot, mode, startProvider);
      } else if (startProvider === "local") {
        // LOCAL routes execute without provider lane locks.
      } else if (startProvider === "deepseek") {
        try {
          releaseSlot = acquireProviderSlot(this.lockRoot, mode, "deepseek");
        } catch (error) {
          if (!isProviderCapacityError(error)) throw error;
          const candidate = withResultSemantics({
            execution_status: "PROVIDER_ERROR",
            evidence_verdict: "UNRESOLVED",
          });
          const fallbackRoute = this.selectFallbackRoute(task, candidate, 0, failureState);
          const fallbackFailureState = fallbackRoute
            ? failureState[fallbackStateKey(fallbackRoute)]
            : null;
          const fallbackOpen = this.fallbackCircuitIsOpen(
            fallbackFailureState,
            this.nowFunction(),
          );
          if (!fallbackRoute || fallbackOpen) {
            taskLock?.release?.();
            taskLock = null;
            return this.createImmediateResult(
              id,
              task,
              cacheKey,
              fallbackOpen
                ? { execution_status: "BLOCKED", evidence_verdict: "UNRESOLVED" }
                : candidate,
              fallbackOpen
                ? "Primary capacity is unavailable and the fallback circuit is open."
                : "The primary reader lane is busy and fallback is not authorized.",
              "primary-reader-saturated-not-fallback-eligible",
            );
          }
          startProvider = fallbackRouteProviderSlot(fallbackRoute).provider;
          startFallbackRoute = fallbackRoute;
          startReason = "primary-reader-saturated";
          try {
            releaseSlot = acquireProviderSlot(this.lockRoot, mode, startProvider);
          } catch (fallbackError) {
            if (isProviderCapacityError(fallbackError)) {
              throw new Error("all canonical reader lanes are busy");
            }
            throw fallbackError;
          }
        }
      } else {
        releaseSlot = acquireProviderSlot(this.lockRoot, mode, startProvider);
      }
      const fallbackProfile = startProvider === "deepseek"
        ? null
        : startProvider === "local"
          ? null
          : resolveFallbackProfile(startFallbackRoute);
      const attemptRoute = startProvider === "deepseek"
        ? primaryRoutePolicyKey(task)
        : startProvider === "local"
          ? LOCAL_ROUTE_LABEL
          : startFallbackRoute;
      const attemptModel = startProvider === "deepseek"
        ? task.model
        : startProvider === "local"
          ? task.localExactWrite
            ? LOCAL_EXACT_WRITE_MODEL
            : task.model
          : fallbackProfile.model;
      task = this.withAttemptIdentity(id, task, 1, attemptRoute, attemptModel);
      mkdirSync(directory, { recursive: true });
      const auditPath = path.join(directory, "deepseek-api.jsonl");
      writeFileSync(auditPath, "", "utf8");
      this.persistJobInputs(directory, id, task, cacheKey, {
        requestExtra: {
          provider: startProvider === "deepseek"
            ? task.primaryRoute
            : startProvider === "local"
            ? LOCAL_ROUTE_LABEL
            : fallbackProfile.provider,
        },
      });
      this.persistAttemptEnvelope(
        directory,
        id,
        task,
        cacheKey,
        startProvider === "deepseek"
          ? task.primaryRoute
          : startProvider === "local"
          ? LOCAL_ROUTE_LABEL
          : fallbackProfile.provider,
      );
      const startedAt = new Date().toISOString();
      const job = {
        job_id: id,
        task_id: task.taskId,
        status: "RUNNING",
        mode,
        tier: task.tier,
        model: startProvider === "deepseek"
          ? task.model
          : startProvider === "local"
          ? task.localExactWrite
            ? LOCAL_EXACT_WRITE_MODEL
            : task.model
          : fallbackProfile.model,
        provider: startProvider === "deepseek"
          ? task.primaryRoute
          : startProvider === "local"
          ? LOCAL_ROUTE_LABEL
          : fallbackProfile.provider,
        coverage_status: task.coverageStatus,
        submitted_at: startedAt,
        started_at: startedAt,
        cache_hit: false,
        cache_key: cacheKey,
        owner_pid: process.pid,
        job_directory: directory,
        ...this.origin,
      };
      atomicJson(path.join(directory, "job.json"), job);

      const controller = new AbortController();
      const activeRecord = {
        controller,
        releaseSlot,
        releaseTaskLock: taskLock?.release ?? (() => {}),
        task,
        directory,
        cacheKey,
        taskFingerprint,
        startProvider,
        startReason,
        startFallbackRoute,
        localCommandSnapshots: localCapture?.commandSnapshots ?? null,
        localSnapshotRoot: localCapture?.snapshotRoot ?? null,
        evidenceContext: task.inputManifest
          ? {
              manifest: task.inputManifest,
              jobId: id,
              workspaceInstanceId: task.workspaceInstanceId,
              receiptSink: (receipt) => appendFileSync(
                path.join(directory, "evidence-receipts.jsonl"),
                `${JSON.stringify(receipt)}\n`,
                "utf8",
              ),
              persistedStateSource: () => {
                const contract = readJson(path.join(directory, "contract.json"));
                const envelope = readJson(path.join(directory, "envelope.json"));
                const manifest = readJson(path.join(directory, "input-manifest.json"));
                const coverage = readJson(path.join(directory, "coverage-spec.json"));
                if (canonicalHash(contract) !== task.contractHash) {
                  throw new Error("persisted contract identity changed");
                }
                if (
                  envelope.job_id !== id ||
                  envelope.workspace_instance_id !== task.workspaceInstanceId ||
                  envelope.attempt_id !== task.attemptId ||
                  envelope.contract_hash !== task.contractHash ||
                  envelope.input_manifest_hash !== task.inputManifestHash ||
                  envelope.coverage_hash !== task.coverageHash ||
                  stableJson(envelope.protocols) !== stableJson(PROTOCOLS) ||
                  stableJson(envelope.protocol_versions) !== stableJson(PROTOCOLS)
                ) {
                  throw new Error("persisted envelope identity changed");
                }
                if (manifest.manifest_hash !== task.inputManifestHash) {
                  throw new Error("persisted manifest identity changed");
                }
                if (
                  coverage.coverage_hash !== task.coverageHash ||
                  canonicalHash(coverage.coverage_spec) !== task.coverageHash
                ) {
                  throw new Error("persisted coverage identity changed");
                }
                const receiptText = readFileSync(
                  path.join(directory, "evidence-receipts.jsonl"),
                  "utf8",
                );
                const persistedReceipts = receiptText.split(/\r?\n/)
                  .filter(Boolean)
                  .map((line) => JSON.parse(line));
                return {
                  manifest,
                  coverageSpec: coverage.coverage_spec,
                  receipts: persistedReceipts,
                };
              },
            }
          : null,
        cancelled: false,
        timedOut: false,
        deadlineMs: this.nowFunction() + task.timeoutMs,
        timeoutHandle: null,
        resourcesReleased: false,
        cancellationPublished: false,
      };
      this.active.set(id, activeRecord);
      activeRecord.timeoutHandle = this.timerFunction(() => {
        const current = this.active.get(id);
        if (!current) return;
        current.timedOut = true;
        current.controller.abort();
      }, task.timeoutMs);
      activeRecord.timeoutHandle?.unref?.();
      void this.runActiveJob(id, job, activeRecord, auditPath);
      return publicJobState(job);
    } catch (error) {
      if (localCapture?.snapshotRoot) {
        rmSync(localCapture.snapshotRoot, { recursive: true, force: true });
      }
      releaseSlot?.();
      taskLock?.release?.();
      throw error;
    }
  }

  releaseActiveResources(active) {
    if (active.resourcesReleased) return;
    active.resourcesReleased = true;
    if (active.timeoutHandle) this.clearTimerFunction(active.timeoutHandle);
    active.releaseSlot();
    active.releaseTaskLock();
  }

  finishActive(id, active) {
    this.releaseActiveResources(active);
    if (active.localSnapshotRoot) {
      rmSync(active.localSnapshotRoot, { recursive: true, force: true });
    }
    if (this.active.get(id) === active) this.active.delete(id);
  }

  publishCancellation(id, active, summary = "Job cancelled.") {
    if (active.cancellationPublished) return;
    active.cancelled = true;
    active.controller.abort();
    const finishedAt = new Date().toISOString();
    const jobPath = path.join(active.directory, "job.json");
    const job = readJson(jobPath);
    if (job.status !== "RUNNING") return;
    const normalized = {
      ...this.failureHandoff("CANCELLED", summary),
      status: "CANCELLED",
      execution_status: "CANCELLED",
    };
    const resultPath = path.join(active.directory, "result.json");
    const result = {
      job_id: id,
      provider: job.provider ?? null,
      ...normalized,
      coverage_status: active.task.coverageStatus,
      cache_hit: false,
      finished_at: finishedAt,
      usage: emptyUsage(),
      api_calls: 0,
      provider_route: [job.provider].filter(Boolean),
      fallback: { used: false, reason: "cancelled", attempt: 0, primary_error: null },
      provider_usage: {
        primary: null,
        luna: null,
        glm: null,
        local: active.startProvider === "local"
          ? { status: "CANCELLED", runs: 1, commands: 0, writes: 0 }
          : null,
      },
      result_path: resultPath,
      sol_handoff: compactSolHandoff(normalized, { resultPath }),
    };
    atomicJson(resultPath, result);
    job.status = normalized.status;
    job.execution_status = normalized.execution_status;
    job.evidence_verdict = normalized.evidence_verdict;
    job.finished_at = finishedAt;
    atomicJson(jobPath, job);
    active.cancellationPublished = true;
    this.releaseActiveResources(active);
  }

  async runActiveJob(id, job, active, auditPath) {
    let normalized;
    let usage = emptyUsage();
    let apiCalls = 0;
    let actualServiceTier = null;
    let deepseekError = null;
    let primaryObservability = null;
    let primaryPackedEvidence = null;
    let fallbackFailureClass = null;
    const fallbackProfile = active.startProvider === "deepseek"
      ? null
      : active.startProvider === "local"
        ? null
        : resolveFallbackProfile(active.startFallbackRoute);
    let providerRoute = [
      active.startProvider === "deepseek"
        ? active.task.primaryRoute
        : active.startProvider === "local"
          ? LOCAL_ROUTE_LABEL
          : fallbackProfile.provider,
    ];
    let fallback = { used: false, reason: null, attempt: 0, primary_error: null };
    const fallbackUsage = {
      luna: null,
      glm: null,
    };
    let localUsage = null;
    if (active.startProvider === "local") {
      try {
        const localResponse = active.task.localExactWrite
          ? await runLocalExactWriteContract(active.task)
          : await runLocalReadContract(active.task, {
              commandRunner: this.commandRunner,
              maximumOutputBytes: MAX_LOCAL_OUTPUT_BYTES,
              maximumReceiptStreamBytes: MAX_LOCAL_RECEIPT_STREAM_BYTES,
              hashText: (value) => sha256(String(value)),
              signal: active.controller.signal,
              deadlineMs: active.deadlineMs,
              nowFunction: this.nowFunction,
              commandSnapshots: active.localCommandSnapshots,
              verifySnapshot: verifyLocalCommandSnapshot,
            });
        normalized = this.redact(withResultSemantics(localResponse));
        usage = localResponse.usage;
        localUsage = {
          status: normalized.status,
          runs: 1,
          commands: active.task.localExactWrite
            ? 0
            : Number(localResponse.receipts?.length) || 0,
          writes: active.task.localExactWrite ? 1 : 0,
        };
      } catch (error) {
        localUsage = {
          status: "FAIL",
          runs: 1,
          commands: 0,
          writes: 0,
        };
        normalized = active.timedOut
          ? this.failureHandoff(
              "BLOCKED",
              `Local route job timed out after ${Math.round(active.task.timeoutMs / 60_000)} minutes.`,
            )
          : active.cancelled
            ? this.failureHandoff("CANCELLED", "Job cancelled by Sol.")
            : this.failureHandoff("INCOMPLETE", error);
        if (active.timedOut || active.cancelled) {
          fallbackFailureClass = "STOP_FOR_SOL";
        } else {
          fallbackFailureClass = "NONRETRYABLE_TASK";
        }
      }
    } else if (active.startProvider !== "deepseek") {
      const state = this.readFailureState();
      const prior = this.primaryFailureState(state).tasks[active.taskFingerprint];
      fallback = {
        used: true,
        reason:
          active.startReason ??
          (prior?.failure_class === "TRANSIENT_READ_ONLY"
            ? "previous-transient-primary-retry-exhausted"
            : "previous-nonretryable-primary-failure"),
        attempt: active.startReason === "primary-route-not-authorized" ? 0 : Number(prior?.deepseek_attempts) || 1,
        primary_error: active.startReason ?? null,
      };
      try {
        requireRouteBudgetController(
          this.budgetController,
          active.startFallbackRoute,
        );
        const fallbackResponse = await this.lunaRunner(active.task, {
          jobDirectory: active.directory,
          signal: active.controller.signal,
          fallbackRoute: active.startFallbackRoute,
          budgetController: this.budgetController,
          fetchFunction: this.fetchFunction,
          commandRunner: this.commandRunner,
          evidenceContext: active.evidenceContext,
          audit: (event) => appendFileSync(
            auditPath,
            `${JSON.stringify(this.redact(event))}\n`,
            "utf8",
          ),
        });
        normalized = this.redact(withResultSemantics(fallbackResponse.handoff));
        fallbackUsage[fallbackStateKey(active.startFallbackRoute)] = fallbackProviderEvidence(
          fallbackResponse,
          active.startFallbackRoute,
        );
        this.recordProviderOutcome(fallbackRouteFromProvider(active.startProvider), active.taskFingerprint, {
          status: normalized.status,
          failureClass: "SUCCESS",
        });
      } catch (error) {
          normalized = active.timedOut
            ? this.failureHandoff(
                "BLOCKED",
                `DeepLuna job timed out after ${Math.round(active.task.timeoutMs / 60_000)} minutes.`,
              )
            : active.cancelled
              ? this.failureHandoff("CANCELLED", "Job cancelled by Sol.")
              : error?.code === "CUMULATIVE_BUDGET_CONTROLLER_UNAVAILABLE"
                ? this.failureHandoff("BLOCKED", error)
              : error?.glmPreflightBlocked === true
                ? this.failureHandoff("BLOCKED", error)
                : error?.lunaProviderStarted === false
                ? this.failureHandoff("INCOMPLETE", error)
                : this.failureHandoff("PROVIDER_ERROR", error);
          const fallbackStarted = error?.lunaProviderStarted !== false;
          if (!active.cancelled && !active.timedOut && fallbackStarted) {
            this.recordProviderOutcome(fallbackRouteFromProvider(active.startProvider), active.taskFingerprint, {
              status: normalized.status,
              failureClass: "PROVIDER_FAILURE",
            });
          }
          if (active.timedOut || active.cancelled) {
            fallbackFailureClass = "STOP_FOR_SOL";
          } else if (error?.lunaProviderStarted === false) {
            fallbackFailureClass = "NONRETRYABLE_TASK";
          } else {
            fallbackFailureClass = "PROVIDER_FAILURE";
          }
        }
    } else {
      try {
        const response = await runDeepSeekAgent(active.task, {
          apiKey: this.apiKey,
          fetchFunction: this.fetchFunction,
          budgetController: this.budgetController,
          negativeAdmissionCoordinator: this.negativeAdmissionCoordinator,
          signal: active.controller.signal,
          commandRunner: this.commandRunner,
          evidenceContext: active.evidenceContext,
          audit: (event) => appendFileSync(
            auditPath,
            `${JSON.stringify(this.redact(event))}\n`,
            "utf8",
          ),
        });
        normalized = this.redact(withResultSemantics(response.handoff));
        usage = response.usage;
        apiCalls = response.api_calls;
        actualServiceTier = response.service_tier;
        primaryObservability = response.observability ?? null;
        primaryPackedEvidence = response.packed_evidence ?? null;
      } catch (error) {
        deepseekError = error;
        usage = error?.deepseekUsage ?? usage;
        apiCalls = Number(error?.deepseekApiCalls) || apiCalls;
        primaryObservability = error?.deepseekObservability ?? null;
        if (active.timedOut) {
          normalized = {
            ...this.failureHandoff(
              "BLOCKED",
              `Direct DeepSeek worker timed out after ${Math.round(active.task.timeoutMs / 60_000)} minutes.`,
            ),
            residual_risks: ["Review the API audit before changing the timeout or resubmitting."],
          };
        } else if (active.cancelled) {
          normalized = this.failureHandoff("CANCELLED", "Job cancelled by Sol.");
        } else if (
          error?.accountingUncertain === true ||
          error?.code === "ACCOUNTING_UNCERTAIN"
        ) {
          normalized = {
            ...this.failureHandoff("BLOCKED", error),
            error_code: "ACCOUNTING_UNCERTAIN",
          };
        } else if (error?.code === MAXIMUM_PROVIDER_CALLS_EXHAUSTED) {
          normalized = {
            ...this.failureHandoff("BLOCKED", error),
            error_code: MAXIMUM_PROVIDER_CALLS_EXHAUSTED,
          };
        } else if (
          error?.executionStatus === "BLOCKED" &&
          new Set([
            "REPEATED_PROVIDER_PROGRESS",
            "REPEATED_PROVIDER_QUESTION",
            "DEGENERATE_PROVIDER_OUTPUT",
          ]).has(error?.code)
        ) {
          normalized = {
            ...this.failureHandoff("BLOCKED", error),
            error_code: error.code,
          };
        } else if (isDeterministicRequestRejection(error)) {
          normalized = {
            ...this.failureHandoff("CONTRACT_ERROR", error),
            error_code: error?.negativeAdmissionHit
              ? "NEGATIVE_ADMISSION"
              : "DETERMINISTIC_REQUEST_REJECTED",
            http_status: error?.httpStatus ?? null,
            negative_admission: Boolean(error?.negativeAdmissionHit),
          };
        } else {
          const providerError = new Set(["TRANSIENT", "PROVIDER_UNAVAILABLE"])
            .has(error?.deepseekFailureClass);
          normalized = this.failureHandoff(
            providerError ? "PROVIDER_ERROR" : "INCOMPLETE",
            error,
          );
        }
      }
    }
    if (active.cancelled && active.cancellationPublished) {
      this.finishActive(id, active);
      return;
    }
    let failureState = this.readFailureState();
    const failureClass = active.startProvider === "deepseek"
      ? classifyDeepSeekFailure(active.task, {
        handoff: normalized,
        error: deepseekError,
        timedOut: active.timedOut,
        cancelled: active.cancelled,
      })
      : (fallbackFailureClass ?? classifyDeepSeekFailure(active.task, {
        handoff: normalized,
        error: deepseekError,
        timedOut: active.timedOut,
        cancelled: active.cancelled,
      }));
    if (
      active.startProvider === "deepseek" &&
      failureClass !== "DETERMINISTIC_REQUEST_REJECTED" &&
      deepseekError?.accountingUncertain !== true &&
      deepseekError?.code !== "ACCOUNTING_UNCERTAIN"
    ) {
      failureState = this.recordProviderOutcome("primary", active.taskFingerprint, {
        status: normalized.status,
        failureClass,
      });
    }
    const taskFailure = this.primaryFailureState(failureState).tasks[active.taskFingerprint];
    const attempts = Number(taskFailure?.deepseek_attempts) || 1;
    const fallbackRoute = this.selectFallbackRoute(active.task, normalized, attempts, failureState);
    const shouldUseFallback =
      active.startProvider === "deepseek" &&
      !active.cancelled &&
      Boolean(fallbackRoute);
    if (shouldUseFallback) {
      const fallbackAttemptProfile = resolveFallbackProfile(fallbackRoute);
      const fallbackProvider = fallbackRouteProviderSlot(fallbackRoute).provider;
      const reason =
        failureClass === "TRANSIENT_READ_ONLY"
          ? "transient-primary-retry-exhausted"
          : "nonretryable-primary-failure";
      providerRoute.push(fallbackAttemptProfile.provider);
      fallback = {
        used: true,
        reason,
        attempt: attempts,
        primary_error: normalized?.summary ?? null,
      };
      let fallbackRouteStarted = false;
      try {
        const lunaTask = this.withAttemptIdentity(
          id,
          active.task,
          Number(active.task.attemptOrdinal) + 1,
          fallbackRoute,
          fallbackAttemptProfile.model,
        );
        this.persistAttemptEnvelope(
          active.directory,
          id,
          lunaTask,
          active.cacheKey,
          fallbackAttemptProfile.provider,
        );
        requireRouteBudgetController(this.budgetController, fallbackRoute);
        fallbackRouteStarted = true;
        const fallbackResponse = await this.lunaRunner(lunaTask, {
          jobDirectory: active.directory,
          signal: active.controller.signal,
          fallbackRoute,
          budgetController: this.budgetController,
        });
        normalized = this.redact(withResultSemantics(fallbackResponse.handoff));
        fallbackUsage[fallbackStateKey(fallbackRoute)] = fallbackProviderEvidence(
          fallbackResponse,
          fallbackRoute,
        );
        this.recordProviderOutcome(fallbackProvider, active.taskFingerprint, {
          status: normalized.status,
          failureClass: "SUCCESS",
        });
      } catch (error) {
        const fallbackStarted = fallbackRouteStarted && error?.lunaProviderStarted !== false;
        normalized = active.timedOut
          ? this.failureHandoff(
              "BLOCKED",
              `DeepLuna job timed out after ${Math.round(active.task.timeoutMs / 60_000)} minutes.`,
            )
          : active.cancelled
            ? this.failureHandoff("CANCELLED", "Job cancelled by Sol.")
            : error?.code === "CUMULATIVE_BUDGET_CONTROLLER_UNAVAILABLE"
              ? this.failureHandoff("BLOCKED", error)
              : fallbackStarted
                ? this.failureHandoff("PROVIDER_ERROR", error)
                : this.failureHandoff("INCOMPLETE", error);
        if (!active.cancelled && !active.timedOut && fallbackStarted) {
          this.recordProviderOutcome(fallbackProvider, active.taskFingerprint, {
            status: normalized.status,
            failureClass: "PROVIDER_FAILURE",
          });
        }
      }
      }
    if (active.timeoutHandle) this.clearTimerFunction(active.timeoutHandle);
    const finishedAt = new Date().toISOString();
    const resultPath = path.join(active.directory, "result.json");
    const result = {
      job_id: id,
      provider: providerRoute[0] ?? null,
      ...normalized,
      coverage_status: normalized.coverage_status ?? active.task.coverageStatus,
      cache_hit: false,
      finished_at: finishedAt,
      usage,
      api_calls: apiCalls,
      provider_route: providerRoute,
      fallback,
      ...(primaryPackedEvidence
        ? { packed_evidence: primaryPackedEvidence }
        : {}),
      provider_usage: {
        primary: active.startProvider === "local"
          ? null
          : {
              profile_id: active.task.primaryProfile,
              provider: active.task.primaryProvider,
              route: active.task.primaryRoute,
              model: active.task.model,
              service_tier: active.task.serviceTier,
              actual_service_tier: actualServiceTier,
               reasoning_effort: active.task.reasoningEffort,
               usage,
               api_calls: apiCalls,
               ...(primaryObservability
                 ? { observability: primaryObservability }
                 : {}),
               ...(primaryPackedEvidence
                 ? { packed_evidence: primaryPackedEvidence }
                 : {}),
             },
        ...fallbackUsage,
        local: localUsage,
      },
      raw_output_path: auditPath,
      result_path: resultPath,
      sol_handoff: compactSolHandoff(normalized, { resultPath }),
    };
    atomicJson(resultPath, result);
    job.status = normalized.status;
    job.execution_status = normalized.execution_status;
    job.evidence_verdict = normalized.evidence_verdict;
    job.finished_at = finishedAt;
    atomicJson(path.join(active.directory, "job.json"), job);
    if (active.cacheKey && isAcceptedResult(normalized)) {
      const cached = {
        ...result,
        status: "PASS",
        execution_status: "ACCEPTED",
        evidence_verdict: result.evidence_verdict ?? "NOT_APPLICABLE",
        cache_hit: false,
        cache_key: active.cacheKey,
        project_id: this.projectId,
        protocols: PROTOCOLS,
        route_constraints: active.task.routeConstraints ?? null,
        contract_hash: active.task.contractHash,
        input_manifest_hash: active.task.inputManifestHash,
        coverage_hash: active.task.coverageHash,
      };
      for (const field of [
        "job_id",
        "job_directory",
        "result_path",
        "raw_output_path",
        "source_cache_path",
        "sol_handoff",
      ]) delete cached[field];
      atomicJson(this.cachePath(active.cacheKey), cached);
    }
    this.finishActive(id, active);
  }

  failureHandoff(executionStatus, summary) {
    const aliases = { PASS: "ACCEPTED", FAIL: "INCOMPLETE" };
    const semantics = normalizeResult({
      execution_status: aliases[executionStatus] ?? executionStatus,
      evidence_verdict: executionStatus === "PASS" ? "NOT_APPLICABLE" : "UNRESOLVED",
    });
    const safeSummary = this.safeSummary(summary);
    return {
      status: legacyStatus(semantics),
      execution_status: semantics.execution_status,
      evidence_verdict: semantics.evidence_verdict,
      summary: safeSummary,
      files_inspected: [],
      files_changed: [],
      commands_run: [],
      tests: [],
      positive_findings: [],
      negative_findings: [safeSummary],
      scientific_uncertainty: false,
      architecture_uncertainty: false,
      scope_deviation: false,
      residual_risks: [],
      recommended_next_action: "Return to Sol for review.",
    };
  }

  status(id, { includeHandoff = false } = {}) {
    if (!/^(?:DS|DJ)-[A-Za-z0-9-]+$/.test(id)) throw new Error("invalid job_id");
    const directory = path.join(this.jobsRoot, id);
    const jobPath = path.join(directory, "job.json");
    if (!existsSync(jobPath)) {
      const legacyPath = path.join(this.legacyJobsRoot, id, "job.json");
      if (existsSync(legacyPath)) {
        return {
          job_id: id,
          evidence_id: id,
          status: "LEGACY_UNOWNED",
          execution_status: "BLOCKED",
          evidence_verdict: "UNRESOLVED",
          coverage_status: "NOT_REQUESTED",
          summary:
            "Legacy evidence predates Codex-task ownership and is available only through local audited migration.",
          cache_hit: false,
        };
      }
      throw new Error(`unknown job_id: ${id}`);
    }
    const job = readJson(jobPath);
    assertOriginOwns(job, this.origin);
    if (job.waiting_for_cache && job.status === "RUNNING") {
      return this.completeCacheWaiter(job, directory);
    }
    const resultPath = path.join(directory, "result.json");
    return publicJobState(
      job,
      existsSync(resultPath) ? readJson(resultPath) : null,
      { includeHandoff },
    );
  }

  cancel(id) {
    if (!/^(?:DS|DJ)-[A-Za-z0-9-]+$/.test(id)) throw new Error("invalid job_id");
    const jobPath = path.join(this.jobsRoot, id, "job.json");
    if (!existsSync(jobPath)) {
      if (existsSync(path.join(this.legacyJobsRoot, id, "job.json"))) {
        throw new Error("legacy evidence cannot be cancelled");
      }
      return { job_id: id, cancelled: false, reason: "job is not known to this project" };
    }
    assertOriginOwns(readJson(jobPath), this.origin);
    const active = this.active.get(id);
    if (!active) return { job_id: id, cancelled: false, reason: "job is not active in this server" };
    if (active.cancelled) {
      return { job_id: id, cancelled: false, reason: "job is already cancelled" };
    }
    if (active.startProvider === "local") {
      this.publishCancellation(id, active);
    } else {
      active.cancelled = true;
      active.controller.abort();
    }
    return { job_id: id, cancelled: true, reason: "direct API cancellation requested" };
  }

  cancelAll() {
    for (const [id, active] of this.active) {
      if (active.startProvider === "local") {
        this.publishCancellation(
          id,
          active,
          "Job cancelled because the MCP transport closed.",
        );
      } else {
        active.cancelled = true;
        active.controller.abort();
      }
      console.error(this.safeSummary(
        `Cancellation requested for ${id} because the MCP transport closed.`,
      ));
    }
  }
}

export function validateBatchSubmission(raw, { maximumConcurrency = 2 } = {}) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("batch submission must be an object");
  }
  if (!Array.isArray(raw.tasks) || raw.tasks.length < 1 || raw.tasks.length > 20) {
    throw new Error("READ_ONLY batches require 1 to 20 tasks");
  }
  const concurrency = raw.concurrency ?? 1;
  if (
    !Number.isSafeInteger(maximumConcurrency) ||
    maximumConcurrency < 1 ||
    maximumConcurrency > 20
  ) {
    throw new TypeError("maximum batch concurrency must be 1 to 20");
  }
  if (
    !Number.isSafeInteger(concurrency) ||
    concurrency < 1 ||
    concurrency > maximumConcurrency
  ) {
    throw new Error(`batch concurrency must be 1 to ${maximumConcurrency}`);
  }
  const identifiers = new Set();
  const defaultAcceptedVerdicts = ["POSITIVE", "NEGATIVE", "NULL", "MIXED", "NOT_APPLICABLE"];
  const supportedAcceptedVerdicts = new Set(defaultAcceptedVerdicts);
  const tasks = raw.tasks.map((candidate) => {
    const nodeId = String(candidate?.node_id ?? "").trim();
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(nodeId)) {
      throw new Error(`invalid batch node_id: ${nodeId || "<empty>"}`);
    }
    if (identifiers.has(nodeId)) throw new Error(`duplicate batch node_id: ${nodeId}`);
    identifiers.add(nodeId);
    if (candidate.mode && candidate.mode !== "READ_ONLY") {
      throw new Error(`batch node ${nodeId} must be READ_ONLY`);
    }
    const dependsOn = [...new Set(safeArray(candidate.depends_on))];
    const acceptedEvidenceVerdicts = candidate.accepted_evidence_verdicts === undefined
      ? [...defaultAcceptedVerdicts]
      : safeArray(candidate.accepted_evidence_verdicts).map((value) => String(value).toUpperCase());
    if (
      acceptedEvidenceVerdicts.length === 0 ||
      acceptedEvidenceVerdicts.some((verdict) => !supportedAcceptedVerdicts.has(verdict))
    ) {
      throw new Error(
        `batch node ${nodeId} accepted_evidence_verdicts must contain supported accepted verdicts`,
      );
    }
    const {
      node_id: _nodeId,
      depends_on: _dependsOn,
      mode: _mode,
      accepted_evidence_verdicts: _acceptedEvidenceVerdicts,
      ...input
    } = candidate;
    validateSubmission({ ...input, task_id: nodeId }, "READ_ONLY");
    return {
      nodeId,
      dependsOn,
      acceptedEvidenceVerdicts: [...new Set(acceptedEvidenceVerdicts)],
      input: { ...input, task_id: nodeId },
    };
  });
  for (const task of tasks) {
    for (const dependency of task.dependsOn) {
      if (!identifiers.has(dependency)) {
        throw new Error(`batch node ${task.nodeId} has unknown dependency: ${dependency}`);
      }
      if (dependency === task.nodeId) throw new Error("batch dependency cycle detected");
    }
  }
  const remaining = new Map(tasks.map((task) => [task.nodeId, new Set(task.dependsOn)]));
  const ready = [...remaining].filter(([, dependencies]) => dependencies.size === 0).map(([id]) => id);
  let visited = 0;
  while (ready.length > 0) {
    const current = ready.shift();
    visited += 1;
    for (const [id, dependencies] of remaining) {
      if (!dependencies.delete(current) || dependencies.size > 0) continue;
      ready.push(id);
    }
  }
  if (visited !== tasks.length) throw new Error("batch dependency cycle detected");
  return Object.freeze({ concurrency, tasks: Object.freeze(tasks) });
}

function batchId() {
  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace("Z", "Z");
  return `DLB-${timestamp}-${crypto.randomBytes(3).toString("hex")}`;
}

function batchPublicState(state) {
  return {
    batch_id: state.batch_id,
    evidence_id: state.batch_id,
    status: state.status,
    concurrency: state.concurrency,
    worker_job_durability: state.worker_job_durability,
    control_state_lifecycle: state.control_state_lifecycle,
    restart_durable_orchestration: state.restart_durable_orchestration,
    daemon_batch_rpc_active: state.daemon_batch_rpc_active,
    submitted_at: state.submitted_at,
    finished_at: state.finished_at ?? null,
    nodes: (state.nodes ?? []).map((node) => ({
      node_id: node.node_id,
      depends_on: node.depends_on,
      accepted_evidence_verdicts: node.accepted_evidence_verdicts,
      status: node.status,
      execution_status: node.execution_status ?? null,
      evidence_verdict: node.evidence_verdict ?? "UNRESOLVED",
      job_id: node.job_id ?? null,
      evidence_id: node.job_id ?? null,
      cache_hit: Boolean(node.cache_hit),
      summary: truncateWords(node.summary ?? "", 40),
    })),
  };
}

export class BatchManager {
  constructor(jobManager, {
    pollDelayMs = 100,
    readerPoolPolicy = resolveFastReaderPoolPolicy(),
  } = {}) {
    this.jobManager = jobManager;
    this.daemonBacked = jobManager.daemonBacked === true;
    this.client = this.daemonBacked ? jobManager.client : null;
    this.storeRoot = path.resolve(jobManager.baseStoreRoot ?? jobManager.storeRoot ?? defaultStoreRoot());
    this.projectId = jobManager.projectId;
    this.projectRoot = jobManager.projectRoot;
    this.origin = jobManager.origin;
    this.batchesRoot = jobManager.batchesRoot;
    this.pollDelayMs = Math.max(1, Number(pollDelayMs) || 100);
    this.readerPoolPolicy = resolveFastReaderPoolPolicy(readerPoolPolicy);
    assertReaderPoolProject(this.readerPoolPolicy, this.projectId);
    mkdirSync(this.batchesRoot, { recursive: true });
    this.pruneBatches();
    this.recoverInterruptedBatches();
  }

  safeSummary(value, maximum = 500) {
    return safeDiagnosticText(value, [this.jobManager.apiKey], maximum);
  }

  pruneBatches() {
    const retentionDays = Number(this.jobManager.retentionDays) || 30;
    const now = this.jobManager.nowFunction?.() ?? Date.now();
    const cutoff = now - retentionDays * 24 * 60 * 60 * 1_000;
    for (const entry of readdirSync(this.batchesRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const statePath = path.join(this.batchesRoot, entry.name, "batch.json");
      if (!existsSync(statePath)) continue;
      try {
        const state = readJson(statePath);
        if (state.status === "RUNNING") continue;
        const timestamp = Date.parse(state.finished_at ?? state.submitted_at ?? "");
        if (Number.isFinite(timestamp) && timestamp < cutoff) {
          rmSync(path.dirname(statePath), { recursive: true, force: true });
        }
      } catch {
        // Retain malformed batch evidence for manual review.
      }
    }
  }

  recoverInterruptedBatches() {
    for (const entry of readdirSync(this.batchesRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = path.join(this.batchesRoot, entry.name);
      const statePath = path.join(directory, "batch.json");
      if (!existsSync(statePath)) continue;
      let state;
      try {
        state = readJson(statePath);
      } catch {
        continue;
      }
      if (state.status !== "RUNNING" || processAlive(Number(state.owner_pid))) continue;
      state.status = "BLOCKED";
      state.finished_at = new Date().toISOString();
      state.manifest_path ??= path.join(directory, "manifest.json");
      for (const node of state.nodes ?? []) {
        if (!new Set(["PENDING", "RUNNING"]).has(node.status)) continue;
        node.status = "BLOCKED";
        node.execution_status = "BLOCKED";
        node.evidence_verdict = "UNRESOLVED";
        node.summary = "Blocked after a DeepLuna batch process interruption; inspect child evidence before resubmitting.";
      }
      this.persist(state, directory);
    }
  }

  persist(state, directory) {
    const manifest = {
      process_name: PROCESS_NAME,
      batch_id: state.batch_id,
      status: state.status,
      concurrency: state.concurrency,
      worker_job_durability: state.worker_job_durability,
      control_state_lifecycle: state.control_state_lifecycle,
      restart_durable_orchestration: state.restart_durable_orchestration,
      daemon_batch_rpc_active: state.daemon_batch_rpc_active,
      submitted_at: state.submitted_at,
      finished_at: state.finished_at ?? null,
      nodes: state.nodes.map((node) => ({
        node_id: node.node_id,
        depends_on: node.depends_on,
        accepted_evidence_verdicts: node.accepted_evidence_verdicts,
        status: node.status,
        execution_status: node.execution_status ?? null,
        evidence_verdict: node.evidence_verdict ?? "UNRESOLVED",
        job_id: node.job_id ?? null,
        cache_hit: Boolean(node.cache_hit),
        summary: truncateWords(node.summary ?? "", 40),
        evidence_id: node.job_id ?? null,
      })),
    };
    atomicJson(path.join(directory, "batch.json"), { ...state, nodes: manifest.nodes });
    atomicJson(state.manifest_path, manifest);
  }

  async submit(raw) {
    if (this.readerPoolPolicy.mode === "FIXED_FIVE_SWARM") {
      const tasks = Array.isArray(raw?.tasks) ? raw.tasks : [];
      if (
        raw?.concurrency !== 5 ||
        tasks.length !== 5 ||
        tasks.some((task) => safeArray(task?.depends_on).length > 0)
      ) {
        throw new Error(
          "fixed five-worker swarm requires exactly five independent tasks at concurrency 5",
        );
      }
    }
    const validated = validateBatchSubmission(raw, {
      maximumConcurrency: this.jobManager.daemonBacked ? 20 : 2,
    });
    const id = batchId();
    const directory = path.join(this.batchesRoot, id);
    mkdirSync(directory, { recursive: true });
    const now = new Date().toISOString();
    const state = {
      batch_id: id,
      status: "RUNNING",
      concurrency: validated.concurrency,
      worker_job_durability: this.daemonBacked ? "DURABLE_DAEMON" : "EMBEDDED_PROCESS",
      control_state_lifecycle: this.daemonBacked
        ? "CLIENT_LIFETIME_EPHEMERAL_WITH_LOCAL_CHECKPOINTS"
        : "PROCESS_LIFETIME_WITH_LOCAL_CHECKPOINTS",
      restart_durable_orchestration: false,
      daemon_batch_rpc_active: false,
      submitted_at: now,
      finished_at: null,
      owner_pid: process.pid,
      ...this.origin,
      manifest_path: path.join(directory, "manifest.json"),
      nodes: validated.tasks.map((task) => ({
        node_id: task.nodeId,
        depends_on: task.dependsOn,
        accepted_evidence_verdicts: task.acceptedEvidenceVerdicts,
        status: "PENDING",
        execution_status: null,
        evidence_verdict: "UNRESOLVED",
        job_id: null,
        cache_hit: false,
        summary: "",
        result_path: null,
      })),
    };
    atomicJson(path.join(directory, "request.json"), {
      batch_id: id,
      ...this.origin,
      concurrency: validated.concurrency,
      tasks: validated.tasks,
    });
    this.persist(state, directory);
    void this.runBatch(state, validated.tasks, directory).catch((error) => {
      state.status = "BLOCKED";
      state.finished_at = new Date().toISOString();
      for (const node of state.nodes.filter((candidate) => candidate.status === "PENDING")) {
        node.status = "BLOCKED";
        node.execution_status = "BLOCKED";
        node.evidence_verdict = "UNRESOLVED";
        node.summary = this.safeSummary(`Batch scheduler stopped: ${error?.message ?? String(error)}`);
      }
      this.persist(state, directory);
    });
    return batchPublicState(state);
  }

  async runNode(node, task, state, directory) {
    node.status = "RUNNING";
    this.persist(state, directory);
    try {
      let result = await this.jobManager.submit(task.input, "READ_ONLY");
      node.job_id = result.job_id ?? null;
      while (new Set(["QUEUED", "RUNNING"]).has(result.status)) {
        await new Promise((resolve) => setTimeout(resolve, this.pollDelayMs));
        result = await this.jobManager.status(node.job_id);
      }
      const normalized = withResultSemantics(
        redactDiagnostic(result, [this.jobManager.apiKey]),
      );
      node.status = new Set(["PASS", "CACHED", "FAIL", "BLOCKED"]).has(result.status)
        ? result.status === "CACHED" ? "CACHED" : normalized.status
        : "FAIL";
      node.execution_status = normalized.execution_status;
      node.evidence_verdict = normalized.evidence_verdict;
      node.cache_hit = Boolean(result.cache_hit);
      node.summary = this.safeSummary(
        result.summary ?? `${node.node_id} completed with ${node.status}`,
      );
      node.result_path = result.result_path ?? null;
      if (
        new Set(["PASS", "CACHED"]).has(node.status) &&
        node.execution_status === "ACCEPTED" &&
        !node.accepted_evidence_verdicts.includes(node.evidence_verdict)
      ) {
        node.status = "BLOCKED";
        node.execution_status = "BLOCKED";
        node.summary = this.safeSummary(
          `Worker result was preserved, but evidence verdict ${node.evidence_verdict} ` +
            "is outside this batch node's frozen accepted_evidence_verdicts policy.",
        );
      }
    } catch (error) {
      node.status = "FAIL";
      node.execution_status = "CONTRACT_ERROR";
      node.evidence_verdict = "UNRESOLVED";
      node.summary = this.safeSummary(error);
    }
    this.persist(state, directory);
  }

  async runBatch(state, tasks, directory) {
    const taskById = new Map(tasks.map((task) => [task.nodeId, task]));
    const nodeById = new Map(state.nodes.map((node) => [node.node_id, node]));
    while (state.nodes.some((node) => node.status === "PENDING")) {
      for (const node of state.nodes.filter((candidate) => candidate.status === "PENDING")) {
        const dependencies = node.depends_on.map((id) => nodeById.get(id));
        const terminalDependencies = dependencies.filter(
          (dependency) => !new Set(["PENDING", "RUNNING"]).has(dependency.status),
        );
        if (
          terminalDependencies.some((dependency) => !dependencySatisfied(
            dependency,
            node.accepted_evidence_verdicts,
          ))
        ) {
          node.status = "BLOCKED";
          node.execution_status = "BLOCKED";
          node.evidence_verdict = "UNRESOLVED";
          node.summary = "Blocked because a dependency gate's execution status or evidence verdict did not satisfy this node's frozen policy.";
        }
      }
      this.persist(state, directory);
      const eligible = state.nodes.filter((node) =>
        node.status === "PENDING" &&
        node.depends_on.every((id) => dependencySatisfied(
          nodeById.get(id),
          node.accepted_evidence_verdicts,
        ))
      );
      if (eligible.length === 0) break;
      for (let index = 0; index < eligible.length; index += state.concurrency) {
        const wave = eligible.slice(index, index + state.concurrency);
        await Promise.all(
          wave.map((node) => this.runNode(node, taskById.get(node.node_id), state, directory)),
        );
      }
    }
    const statuses = new Set(state.nodes.map((node) => node.status));
    state.status = [...statuses].every((status) => new Set(["PASS", "CACHED"]).has(status))
      ? "PASS"
      : statuses.has("BLOCKED")
        ? "BLOCKED"
        : "FAIL";
    state.execution_status = state.status === "PASS"
      ? "ACCEPTED"
      : state.status === "BLOCKED" ? "BLOCKED" : "INCOMPLETE";
    state.evidence_verdict = "NOT_APPLICABLE";
    state.finished_at = new Date().toISOString();
    this.persist(state, directory);
  }

  status(id) {
    if (!/^DLB-[A-Za-z0-9-]+$/.test(id)) throw new Error("invalid batch_id");
    const statePath = path.join(this.batchesRoot, id, "batch.json");
    if (!existsSync(statePath)) throw new Error(`unknown batch_id: ${id}`);
    const state = readJson(statePath);
    assertOriginOwns(state, this.origin);
    return batchPublicState(state);
  }

  metrics() {
    const statuses = {};
    let total = 0;
    for (const entry of readdirSync(this.batchesRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      try {
        const state = readJson(path.join(this.batchesRoot, entry.name, "batch.json"));
        total += 1;
        statuses[state.status] = (statuses[state.status] ?? 0) + 1;
      } catch {
        // Ignore incomplete directories during concurrent writes.
      }
    }
    return {
      total,
      statuses,
      worker_job_durability: this.daemonBacked ? "DURABLE_DAEMON" : "EMBEDDED_PROCESS",
      control_state_lifecycle: this.daemonBacked
        ? "CLIENT_LIFETIME_EPHEMERAL_WITH_LOCAL_CHECKPOINTS"
        : "PROCESS_LIFETIME_WITH_LOCAL_CHECKPOINTS",
      restart_durable_orchestration: false,
      daemon_batch_rpc_active: false,
    };
  }
}

const DEFAULT_PROJECT_CEILING_NANO_USD = 1_000_000_000;

export function resolveProjectCeilingNanoUsd(
  value = process.env.DEEPLUNA_PROJECT_CEILING_NANO_USD,
) {
  if (value === undefined || value === null || String(value).trim() === "") {
    return DEFAULT_PROJECT_CEILING_NANO_USD;
  }
  const ceiling = Number(String(value).trim());
  if (!Number.isSafeInteger(ceiling) || ceiling < 1) {
    throw new Error(
      "DEEPLUNA_PROJECT_CEILING_NANO_USD must be a positive safe integer",
    );
  }
  return ceiling;
}

function productionDaemonPaths(storeRoot, projectId) {
  const baseStoreRoot = path.resolve(storeRoot);
  const projectRoot = path.join(baseStoreRoot, "projects", projectId);
  const daemonRoot = path.join(projectRoot, "daemon-v2");
  return Object.freeze({
    baseStoreRoot,
    projectRoot,
    daemonRoot,
    databasePath: path.join(daemonRoot, "scheduler.sqlite3"),
    attestationPath: path.join(daemonRoot, "migration-attestation.json"),
    copyRoot: path.join(daemonRoot, "migration-copy"),
    copiedRoot: path.join(daemonRoot, "migration-copy", "fresh-state"),
  });
}

export async function openProductionCandidateStore({
  storeRoot = defaultStoreRoot(),
  projectId = process.env.DEEPLUNA_PROJECT_ID,
  workspace = process.cwd(),
  now = Date.now,
} = {}) {
  const exactProjectId = resolveProjectId(projectId, workspace);
  const workspaceRoot = realpathSync(path.resolve(workspace));
  const paths = productionDaemonPaths(storeRoot, exactProjectId);
  mkdirSync(paths.daemonRoot, { recursive: true });
  let created = false;
  let upgradedToV5 = false;
  const stamp = `${Date.now()}-${process.pid}`;
  if (!existsSync(paths.databasePath)) {
    created = true;
    const initial = openSchedulerStore({ filename: paths.databasePath, now });
    initial.close();
    await migrateSchedulerStoreToCandidateV3({
      filename: paths.databasePath,
      backupFilename: path.join(
        paths.daemonRoot,
        `scheduler.schema-v2.${stamp}.backup.sqlite3`,
      ),
    });
    await migrateSchedulerStoreToCandidateV4({
      filename: paths.databasePath,
      backupFilename: path.join(
        paths.daemonRoot,
        `scheduler.schema-v3.${stamp}.backup.sqlite3`,
      ),
    });
    await migrateSchedulerStoreToCandidateV5({
      filename: paths.databasePath,
      backupFilename: path.join(
        paths.daemonRoot,
        `scheduler.schema-v4.${stamp}.backup.sqlite3`,
      ),
    });
  } else {
    const probe = new DatabaseSync(paths.databasePath, { readOnly: true });
    let schemaVersion;
    try {
      const rows = probe
        .prepare("SELECT value FROM schema_meta WHERE key='schema_version'")
        .all();
      if (rows.length !== 1 || !["4", "5"].includes(rows[0].value)) {
        throw new Error("production candidate store schema is unsupported");
      }
      schemaVersion = Number(rows[0].value);
    } finally {
      probe.close();
    }
    if (schemaVersion === 4) {
      await migrateSchedulerStoreToCandidateV5({
        filename: paths.databasePath,
        backupFilename: path.join(
          paths.daemonRoot,
          `scheduler.schema-v4.${stamp}.backup.sqlite3`,
        ),
      });
      upgradedToV5 = true;
    }
  }
  const store = openCandidateSchedulerStoreV5({
    filename: paths.databasePath,
    now,
  });
  try {
    let migrationAttestation;
    if (created) {
      mkdirSync(paths.copyRoot, { recursive: true });
      mkdirSync(paths.copiedRoot, { recursive: true });
      const outcome = store.auditCandidateCopiedStateMigration({
        projectId: exactProjectId,
        copyRoot: paths.copyRoot,
        workspaceRoot,
        candidateProtocolVersion: PROTOCOLS.contract,
        staleBeforeMs: 0,
        sources: [{
          namespace: "fresh-state",
          sourceKind: "CANONICAL",
          copiedRoot: paths.copiedRoot,
        }],
      });
      const sourceHashes = Object.fromEntries(
        store.database
          .prepare(
            `SELECT source_namespace,source_hash
             FROM legacy_migration_sources
             WHERE run_id=?
             ORDER BY source_namespace`,
          )
          .all(outcome.runId)
          .map((row) => [row.source_namespace, row.source_hash]),
      );
      migrationAttestation = store.issueCandidateMigrationAttestation({
        projectId: exactProjectId,
        runId: outcome.runId,
        sourceHashes,
      });
      atomicJson(paths.attestationPath, migrationAttestation);
    } else {
      if (!existsSync(paths.attestationPath)) {
        throw new Error("candidate daemon migration attestation is missing");
      }
      migrationAttestation = readJson(paths.attestationPath);
      if (upgradedToV5) {
        migrationAttestation = store.upgradeCandidateMigrationAttestation({
          previousAttestation: migrationAttestation,
          sourceStoreSchemaVersion: 4,
          targetStoreSchemaVersion: 5,
        });
        atomicJson(paths.attestationPath, migrationAttestation);
      }
    }
    const verified = store.verifyCandidateMigrationAttestation(
      migrationAttestation,
    );
    return Object.freeze({
      created,
      migrationAttestation: verified,
      paths,
      projectId: exactProjectId,
      store,
      workspaceRoot,
    });
  } catch (error) {
    store.close();
    throw error;
  }
}

function createProductionWorkerEnvelope(input, mode, session, validated) {
  const requestNonce = crypto.randomBytes(16).toString("hex");
  const taskIdCandidate = String(input?.task_id ?? `task-${requestNonce}`)
    .trim()
    .replace(/[^A-Za-z0-9._:-]/g, "-")
    .slice(0, 64);
  const taskId = taskIdCandidate || `task-${requestNonce}`;
  const identity = sha256(stableJson({
    input,
    mode,
    projectId: session.projectId,
    requestNonce,
  }));
  // REV-9 retry policy: route_constraints.maximum_attempts drives the number of
  // scheduler attempts (429 -> 3 attempts incl. initial, 500 -> 2, 503 -> 3, 400 -> 1).
  // The zod schema bounds it to [1, 3]; validated.routeConstraints is already normalized.
  const requestedAttempts = Number(
    validated?.routeConstraints?.maximumAttempts ??
    input?.route_constraints?.maximum_attempts ??
    1,
  );
  const maximumAttempts = Number.isSafeInteger(requestedAttempts) && requestedAttempts >= 1
    ? Math.min(requestedAttempts, 3)
    : 1;
  return Object.freeze({
    projectId: session.projectId,
    taskId,
    idempotencyKey: `production-${identity}`,
    contractHash: identity,
    inputFingerprint: identity,
    role: mode === "WRITE" ? "WRITER" : "READER",
    poolId: mode === "WRITE" ? "deepluna-write" : "deepluna-read",
    priority: 0,
    maximumAttempts,
    payload: Object.freeze({
      input,
      mode,
      originContext: Object.freeze({
        originThreadHash: session.originThreadHash,
        originCapabilityHash: session.originCapabilityHash,
      }),
      ...(mode === "WRITE"
        ? {
            writerScope: Object.freeze({
              worktreeRoot: validated.workspace,
              outputPaths: Object.freeze(
                validated.allowedPaths.map((relative) =>
                  path.resolve(validated.workspace, relative)
                ),
              ),
            }),
          }
        : {}),
    }),
  });
}

function dynamicPoolSnapshot(storeRoot) {
  const physicalRoot = path.join(
    path.resolve(storeRoot),
    "dynamic-pool-v1",
    "physical",
  );
  mkdirSync(physicalRoot, { recursive: true });
  removeStaleLocks(physicalRoot);
  const names = readdirSync(physicalRoot);
  return Object.freeze({
    activeReads: names.filter((name) => /^reader-\d+\.lock$/.test(name)).length,
    activeWrites: names.filter((name) => name === "writer.lock").length,
  });
}

function productionProjectBudgetSnapshot(store, projectId, configuredCeiling) {
  const accounting = store.getCandidateAccountingHealth({
    projectId,
    expectedPricingVersion: COST_POLICY_VERSION,
    expectedCeilingNanoUsd: configuredCeiling,
  });
  return Object.freeze({
    configured: accounting.configured,
    pricingVersion: accounting.pricingVersion,
    policyMatches: accounting.policyMatches,
    ceilingMatches: accounting.ceilingMatches,
    aggregatesConsistent: accounting.aggregatesConsistent,
    ceiling: accounting.ceilingNanoUsd ?? configuredCeiling,
    spent: accounting.spentNanoUsd,
    reserved: accounting.reservedNanoUsd,
    unknown: accounting.unknownTransmissions,
    active: accounting.activeTransmissions,
  });
}

function productionUnavailableCircuitCount(projectRoot, primaryProfile, nowMs) {
  const statePath = path.join(projectRoot, "worker-state-v5.json");
  if (!existsSync(statePath)) return 0;
  const state = readJson(statePath);
  const open = (entry) => {
    const until = Date.parse(entry?.open_until ?? "");
    return Number.isFinite(until) && until > nowMs;
  };
  return [
    state?.primary_profiles?.[primaryProfile.id],
    state?.luna,
    state?.glm,
  ].filter(open).length;
}

export function classifyProductionCandidateReadiness(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("production readiness input must be an object");
  }
  for (const field of [
    "runtimeAccepted",
    "productionEligible",
    "windowsAclProven",
    "migrationAttested",
    "budgetSafe",
    "accountingConfigured",
    "policyMatches",
    "accountingConsistent",
    "headCapabilityAdvertised",
    "headValidatorActive",
    "headProducerActive",
    "capacityPressure",
  ]) {
    if (typeof input[field] !== "boolean") {
      throw new TypeError(`${field} must be boolean`);
    }
  }
  for (const field of [
    "migrationUnresolvedCollisions",
    "migrationOperationalImports",
    "unknownTransmissions",
    "unavailablePools",
  ]) {
    if (!Number.isSafeInteger(input[field]) || input[field] < 0) {
      throw new TypeError(`${field} must be a nonnegative safe integer`);
    }
  }
  const hardReasons = [];
  if (!input.runtimeAccepted) hardReasons.push("activation-disabled");
  if (!input.productionEligible) hardReasons.push("production-ineligible");
  if (!input.windowsAclProven) hardReasons.push("windows-acl-unproven");
  if (!input.migrationAttested) hardReasons.push("migration-unattested");
  if (input.migrationUnresolvedCollisions > 0) {
    hardReasons.push("migration-collision");
  }
  if (input.migrationOperationalImports > 0) {
    hardReasons.push("operational-imports-present");
  }
  if (input.accountingConfigured && !input.policyMatches) {
    hardReasons.push("cost-policy-mismatch");
  }
  if (!input.accountingConsistent) {
    hardReasons.push("cost-accounting-inconsistent");
  }
  if (!input.budgetSafe || input.unknownTransmissions > 0) {
    hardReasons.push("budget-unsafe");
  }
  if (input.headCapabilityAdvertised && !input.headValidatorActive) {
    hardReasons.push("head-validator-inactive");
  }
  if (input.headCapabilityAdvertised && !input.headProducerActive) {
    hardReasons.push("head-producer-inactive");
  }
  const softReasons = [];
  if (input.capacityPressure) softReasons.push("capacity-pressure");
  if (input.unavailablePools > 0) softReasons.push("provider-circuit-open");
  const reasonCodes = Object.freeze([...hardReasons, ...softReasons]);
  const readiness =
    hardReasons.length > 0
      ? "BLOCKED"
      : softReasons.length > 0
        ? "DEGRADED"
        : "READY";
  return Object.freeze({
    readiness,
    reasonCodes,
    providerCallsEnabled: readiness === "READY",
  });
}

function buildProductionCandidateHealth({
  api,
  session,
  migrationAttestation,
  store,
  storeRoot,
  projectRoot,
  projectCeilingNanoUsd,
  primaryProfile,
  readerPoolPolicy,
  headReadiness = Object.freeze({
    validatorActive: false,
    producerActive: false,
  }),
  nowMs = Date.now(),
}) {
  const metrics = api.projectMetrics();
  const capacity = dynamicPoolSnapshot(storeRoot);
  const exactReaderPoolPolicy = resolveFastReaderPoolPolicy(readerPoolPolicy);
  const budget = productionProjectBudgetSnapshot(
    store,
    session.projectId,
    projectCeilingNanoUsd,
  );
  const unavailablePools = productionUnavailableCircuitCount(
    projectRoot,
    primaryProfile,
    nowMs,
  );
  const budgetSafe =
    BigInt(budget.spent) + BigInt(budget.reserved) + 1n <=
    BigInt(budget.ceiling);
  const classified = classifyProductionCandidateReadiness({
    runtimeAccepted: CANDIDATE_DAEMON_RUNTIME_ACCEPTED,
    productionEligible:
      CANDIDATE_DAEMON_PROFILE.activation.productionActivationEligible,
    windowsAclProven:
      CANDIDATE_DAEMON_PROFILE.activation.windowsAcl === "PROVEN",
    migrationAttested: migrationAttestation.attested === true,
    migrationUnresolvedCollisions: migrationAttestation.unresolvedCollisions,
    migrationOperationalImports: migrationAttestation.operationalImports,
    budgetSafe,
    accountingConfigured: budget.configured,
    policyMatches: budget.policyMatches,
    accountingConsistent:
      budget.aggregatesConsistent && (!budget.configured || budget.ceilingMatches),
    unknownTransmissions: budget.unknown,
    headCapabilityAdvertised:
      CANDIDATE_DAEMON_REQUIRED_CAPABILITIES.includes("sol-head-v1"),
    headValidatorActive: headReadiness.validatorActive === true,
    headProducerActive: headReadiness.producerActive === true,
    capacityPressure:
      capacity.activeReads === exactReaderPoolPolicy.readLimit ||
      capacity.activeWrites === 1 ||
      metrics.queuedJobs > 0,
    unavailablePools,
  });
  return Object.freeze({
    schema_version: 1,
    readiness: classified.readiness,
    reason_codes: classified.reasonCodes,
    runtime_mode: "CANDIDATE_V2",
    server_release: CANDIDATE_DAEMON_RELEASE,
    runtime_build_hash: session.serverHello.runtimeBuildHash,
    process_boot_id: session.serverHello.serverInstanceId,
    process_started_at_ms: session.serverHello.serverStartedAtMs,
    protocol_version: CANDIDATE_DAEMON_PROFILE.protocol,
    rpc_schema_version: CANDIDATE_DAEMON_PROFILE.rpcSchema,
    store_schema_version: CANDIDATE_DAEMON_PROFILE.storeSchema,
    project_id: session.projectId,
    origin_id: session.originId,
    capabilities: CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
    activation: Object.freeze({
      runtime_accepted: CANDIDATE_DAEMON_RUNTIME_ACCEPTED,
      production_eligible:
        CANDIDATE_DAEMON_PROFILE.activation.productionActivationEligible,
      windows_acl: CANDIDATE_DAEMON_PROFILE.activation.windowsAcl,
    }),
    capacity: Object.freeze({
      read_limit: exactReaderPoolPolicy.readLimit,
      write_limit: 1,
      active_reads: capacity.activeReads,
      active_writes: capacity.activeWrites,
      queued: metrics.queuedJobs,
    }),
    migration: Object.freeze({
      attested: migrationAttestation.attested,
      attestation_id: migrationAttestation.attestationId,
      source_set_hash: migrationAttestation.sourceSetHash,
      unresolved_collisions: migrationAttestation.unresolvedCollisions,
      operational_imports: migrationAttestation.operationalImports,
    }),
    budget: Object.freeze({
      spent_nano_usd: budget.spent,
      open_reserved_nano_usd: budget.reserved,
      next_call_estimate_nano_usd: 1,
      project_ceiling_nano_usd: budget.ceiling,
      unknown_reservations: budget.unknown,
    }),
    circuits: Object.freeze({
      provider_calls_enabled: classified.providerCallsEnabled,
      unavailable_pools: unavailablePools,
    }),
  });
}

function assertProductionWorkerSubmission(input, mode, primaryProfile) {
  const validated = validateSubmission(input, mode, primaryProfile, {
    codexOrchestrationEnabled: true,
  });
  if (validated.requiredReads.length > 0) {
    buildTextEvidenceManifest({
      requiredReads: validated.requiredReads,
      resolvePath: (relative) => path.resolve(validated.workspace, relative),
    });
  }
  return validated;
}

export function createProductionLegacyValidators(primaryProfile, {
  projectId,
  projectScope = "project",
  allowedRoots = null,
} = {}) {
  return Object.freeze({
    workerSubmit(input, mode) {
      try {
        assertProductionWorkerSubmission(input, mode, primaryProfile);
        return true;
      } catch {
        return false;
      }
    },
    batchSubmit: () => false,
    headPlan(input) {
      try {
        validateSolRoutePlanInput(input, {
          projectId,
          projectScope,
          allowedRoots,
          primaryProfile,
        });
        return true;
      } catch {
        return false;
      }
    },
  });
}

function createProductionSolHeadBudgetGate({
  store,
  projectId,
  projectCeilingNanoUsd,
}) {
  return Object.freeze({
    isDurableTransmissionController: true,
    get cumulativeBudgetSafe() {
      try {
        const accounting = store.getCandidateAccountingHealth({
          projectId,
          expectedPricingVersion: COST_POLICY_VERSION,
          expectedCeilingNanoUsd: projectCeilingNanoUsd,
        });
        return (
          accounting.aggregatesConsistent &&
          accounting.unknownTransmissions === 0 &&
          accounting.activeTransmissions === 0 &&
          (!accounting.configured ||
            (accounting.policyMatches && accounting.ceilingMatches)) &&
          BigInt(accounting.spentNanoUsd) +
              BigInt(accounting.reservedNanoUsd) +
              1n <=
            BigInt(projectCeilingNanoUsd)
        );
      } catch {
        return false;
      }
    },
    supportsRoute(route) {
      return String(route ?? "").toUpperCase() === "SOL";
    },
    async reserveNextCall() {
      const error = new Error(
        "Sol subscription accounting is enforced by the durable head-attempt gate",
      );
      error.code = "SOL_SUBSCRIPTION_RESERVATION_UNAVAILABLE";
      throw error;
    },
    async reconcile() {
      const error = new Error(
        "Sol subscription settlement is represented by the durable head result",
      );
      error.code = "SOL_SUBSCRIPTION_RECONCILIATION_UNAVAILABLE";
      throw error;
    },
  });
}

function productionCandidatePacketFromHeadResult(result) {
  if (!result || typeof result !== "object" || Array.isArray(result)) {
    throw new TypeError("Sol head result artifact must be an object");
  }
  const status = String(result.status ?? "");
  if (!["PASS", "CACHED", "BLOCKED", "FAIL"].includes(status)) {
    throw new TypeError("Sol head result artifact has an invalid status");
  }
  const handoff =
    result.head_handoff &&
    typeof result.head_handoff === "object" &&
    !Array.isArray(result.head_handoff)
      ? result.head_handoff
      : {};
  const accepted = ["PASS", "CACHED"].includes(status);
  const executionStatus = accepted
    ? "ACCEPTED"
    : result.execution_status === "CANCELLED"
      ? "CANCELLED"
      : status === "BLOCKED"
        ? "BLOCKED"
        : Number(result.model_calls) > 0
          ? "PROVIDER_ERROR"
          : "CONTRACT_ERROR";
  const summary = boundedText(
    handoff.summary ?? result.summary ?? "The bounded Sol head returned no summary.",
    800,
  );
  const decision = boundedText(handoff.decision ?? "", 800);
  const residualRisks = Array.isArray(handoff.residual_risks)
    ? handoff.residual_risks
        .map((item) => boundedText(item, 800))
        .filter(Boolean)
        .slice(0, 32)
    : [];
  return Object.freeze({
    schema_version: 1,
    result_protocol: 3,
    status: status === "CACHED" ? "CACHED" : accepted ? "PASS" : status,
    execution_status: executionStatus,
    evidence_verdict: accepted ? "NOT_APPLICABLE" : "UNRESOLVED",
    cache_hit: status === "CACHED" || result.cache_hit === true,
    summary,
    positive_findings:
      accepted && (decision || summary) ? [decision || summary] : [],
    negative_findings: accepted ? [] : [summary],
    residual_risks: residualRisks,
    recommended_next_action: boundedText(
      handoff.recommended_next_action ??
        "Return the bounded Sol head result to the owning task.",
      800,
    ),
    scientific_uncertainty: handoff.scientific_uncertainty === true,
    architecture_uncertainty:
      handoff.architecture_uncertainty === true || executionStatus === "BLOCKED",
    scope_deviation: handoff.scope_deviation === true,
  });
}

export async function createProductionCandidateDaemon({
  storeRoot = defaultStoreRoot(),
  projectId = process.env.DEEPLUNA_PROJECT_ID,
  projectScope = "project",
  workspace = process.cwd(),
  projectCeilingNanoUsd = resolveProjectCeilingNanoUsd(),
  primaryProfile = resolvePrimaryProfile(),
  readerPoolPolicy = resolveFastReaderPoolPolicy(),
  apiKey = resolvePrimaryApiKey(primaryProfile),
  managerFactory,
  headRunner = runCodexSolHeadAgent,
  headBudgetControllerFactory,
  headProducerEnabled = true,
  isProcessAlive = processAlive,
  pollDelayMs = 50,
  now = Date.now,
} = {}) {
  if (
    typeof headRunner !== "function" ||
    (headBudgetControllerFactory !== undefined &&
      typeof headBudgetControllerFactory !== "function") ||
    typeof headProducerEnabled !== "boolean" ||
    typeof isProcessAlive !== "function"
  ) {
    throw new TypeError("invalid production Sol head configuration");
  }
  const opened = await openProductionCandidateStore({
    storeRoot,
    projectId,
    workspace,
    now,
  });
  const projectSecret = ensureProjectSecret(opened.paths.projectRoot);
  const secret = Buffer.from(projectSecret, "hex");
  const exactProjectScope = resolveProjectScope(projectScope);
  const exactReaderPoolPolicy = resolveFastReaderPoolPolicy(readerPoolPolicy);
  assertReaderPoolProject(exactReaderPoolPolicy, opened.projectId);
  const allowedRoots = Object.freeze([opened.workspaceRoot]);
  const legacyValidators = createProductionLegacyValidators(primaryProfile, {
    projectId: opened.projectId,
    projectScope: exactProjectScope,
    allowedRoots,
  });
  const headRuntimes = new Map();
  let scheduleHeadPump = () => Promise.resolve();
  const headRuntimeForOrigin = ({
    originThreadHash,
    originCapabilityHash,
    originId,
  }) => {
    const key = `${originThreadHash}:${originCapabilityHash}`;
    let runtimeRecord = headRuntimes.get(key);
    if (runtimeRecord !== undefined) return runtimeRecord;
    const budgetController =
      headBudgetControllerFactory === undefined
        ? createProductionSolHeadBudgetGate({
            store: opened.store,
            projectId: opened.projectId,
            projectCeilingNanoUsd,
          })
        : headBudgetControllerFactory({
            store: opened.store,
            projectId: opened.projectId,
            originId,
            projectCeilingNanoUsd,
          });
    const headManager = new HeadJobManager({
      storeRoot: opened.paths.baseStoreRoot,
      projectId: opened.projectId,
      projectScope: exactProjectScope,
      originContext: Object.freeze({
        originThreadHash,
        originCapabilityHash,
      }),
      allowedRoots,
      primaryProfile,
      budgetController,
      solRunner: headRunner,
    });
    runtimeRecord = Object.freeze({
      budgetController,
      handlers: createCandidateInactiveHeadRpcHandlers({ headManager }),
      manager: headManager,
      originCapabilityHash,
      originId,
      originThreadHash,
    });
    headRuntimes.set(key, runtimeRecord);
    return runtimeRecord;
  };
  const headRuntimeForSession = (session) => {
    return headRuntimeForOrigin({
      originThreadHash: session.originThreadHash,
      originCapabilityHash: session.originCapabilityHash,
      originId: session.originId,
    });
  };
  const headRpcHandlers = Object.freeze({
    prepareHeadPlan(context) {
      return headRuntimeForSession(context.session).handlers.prepareHeadPlan(
        context,
      );
    },
    prepareHeadSubmit(context) {
      return headRuntimeForSession(context.session).handlers.prepareHeadSubmit(
        context,
      );
    },
    headPlan(context) {
      return headRuntimeForSession(context.session).handlers.headPlan(context);
    },
    headSubmit(context) {
      const submitted =
        headRuntimeForSession(context.session).handlers.headSubmit(context);
      if (headProducerEnabled) {
        queueMicrotask(() => void scheduleHeadPump().catch(() => {}));
      }
      return submitted;
    },
  });
  const headValidatorActive = legacyValidators.headPlan({
    objective: "Validate one provider-free production Sol plan.",
    workspace: opened.workspaceRoot,
    allowed_paths: ["."],
    forbidden_actions: ["No writes", "No provider calls"],
    commands_tests: [],
    definition_of_done: ["Validate the bounded read-only plan"],
    required_output: ["One provider-free route decision"],
    complexity: 0,
    scientific_claim_risk: 0,
    ambiguity: 0,
    blast_radius: 0,
    oracle_weakness: 0,
    value_at_risk: 0,
    mechanical: false,
    deterministic_oracle: false,
    estimated_work_units: 1,
    current_effort: "xhigh",
    max_output_tokens: MIN_HANDOFF_OUTPUT_TOKENS,
    reuse_cache: true,
  });
  const runner = createProductionCandidateWorkerRunner({
    storeRoot: opened.paths.baseStoreRoot,
    projectId: opened.projectId,
    ...(managerFactory === undefined ? {} : { managerFactory }),
    readerPoolPolicy: exactReaderPoolPolicy,
    pollDelayMs,
  });
  let runtime = null;
  let runtimeAccountingBlocked = false;
  try {
    runtime = createCandidateProjectRuntime({
      mode: CANDIDATE_RUNTIME_MODE,
      accountingMode: CANDIDATE_DURABLE_ACCOUNTING_MODE,
      store: opened.store,
      runner,
      capacityPolicy: resolveCapacityPolicy({
        fastOnly: exactReaderPoolPolicy.fastOnly,
      }),
      now,
      leaseMs: 30_000,
      projectId: opened.projectId,
      budgetControllerFactory({ store, projectId: exactProjectId, originId }) {
        return createDeepLunaDurableBudgetController({
          store,
          projectId: exactProjectId,
          originId,
          projectCeilingNanoUsd,
        });
      },
    });
  } catch (error) {
    if (error?.code !== "COST_ACCOUNTING_CORRUPT") throw error;
    runtimeAccountingBlocked = true;
  }
  let pumpPromise = null;
  const pump = () => {
    if (runtime === null) {
      const error = new Error("daemon activation is disabled");
      error.code = "ACTIVATION_DISABLED";
      return Promise.reject(error);
    }
    if (pumpPromise !== null) {
      runtime.dispatchQueued();
      return pumpPromise;
    }
    pumpPromise = runtime.runUntilIdle().finally(() => {
      pumpPromise = null;
      if (opened.store.listQueuedGenerations().length > 0) {
        queueMicrotask(() => void pump().catch(() => {}));
      }
    });
    return pumpPromise;
  };
  let stopping = false;
  let headPumpPromise = null;
  let headProducerReady = false;
  const headOriginForPlan = (planId) => {
    const row = opened.store.database
      .prepare(
        `SELECT plan.origin_id,origin.origin_thread_hash,
                origin.origin_capability_hash
         FROM sol_plans AS plan
         JOIN origins AS origin
           ON origin.origin_id=plan.origin_id
          AND origin.project_id=plan.project_id
         WHERE plan.plan_id=? AND plan.project_id=?`,
      )
      .get(planId, opened.projectId);
    if (
      row === undefined ||
      !Number.isSafeInteger(row.origin_id) ||
      !/^[a-f0-9]{64}$/.test(row.origin_thread_hash) ||
      !/^[a-f0-9]{64}$/.test(row.origin_capability_hash)
    ) {
      throw new Error("candidate head producer origin identity is unavailable");
    }
    return Object.freeze({
      originId: row.origin_id,
      originThreadHash: row.origin_thread_hash,
      originCapabilityHash: row.origin_capability_hash,
    });
  };
  const headRuntimeForProducer = (producer) => {
    return headRuntimeForOrigin(headOriginForPlan(producer.planId));
  };
  const headArtifactPaths = (producer, origin) => {
    const scoped = projectStorePaths(
      opened.paths.baseStoreRoot,
      opened.projectId,
      {
        scope: exactProjectScope,
        threadScope: origin.originThreadHash,
      },
    );
    const directory = path.join(
      scoped.headsRoot,
      "jobs",
      producer.producerJobId,
    );
    return Object.freeze({
      directory,
      jobPath: path.join(directory, "job.json"),
      resultPath: path.join(directory, "result.json"),
    });
  };
  const exactHeadTerminalArtifact = (producer) => {
    const origin = headOriginForPlan(producer.planId);
    const paths = headArtifactPaths(producer, origin);
    if (!existsSync(paths.jobPath) || !existsSync(paths.resultPath)) return null;
    const job = readJson(paths.jobPath);
    const result = readJson(paths.resultPath);
    if (
      job.job_id !== producer.producerJobId ||
      job.plan_id !== producer.planId ||
      result.job_id !== producer.producerJobId ||
      result.plan_id !== producer.planId ||
      job.status !== result.status ||
      !["PASS", "CACHED", "BLOCKED", "FAIL"].includes(result.status) ||
      job.originThreadHash !== origin.originThreadHash ||
      job.originCapabilityHash !== origin.originCapabilityHash
    ) {
      throw new Error("candidate head terminal artifact identity is incoherent");
    }
    return Object.freeze({
      packet: productionCandidatePacketFromHeadResult(result),
      result,
    });
  };
  const reconcilePriorHeadArtifacts = () => {
    const rows = opened.store.database
      .prepare(
        `SELECT producer.*,run.binding_epoch,run.run_state
         FROM head_producer_attempts AS producer
         JOIN head_runs AS run
           ON run.head_run_id=producer.head_run_id
          AND run.project_id=producer.project_id
         WHERE producer.project_id=?
           AND producer.producer_state IN ('CLAIMED','RUNNING')
         ORDER BY producer.created_at_ms,producer.producer_job_id`,
      )
      .all(opened.projectId);
    for (const row of rows) {
      const alive =
        row.process_boot_id === CANDIDATE_PROCESS_BOOT_ID &&
        isProcessAlive(row.owner_pid) === true;
      if (alive) continue;
      try {
        const artifact = exactHeadTerminalArtifact({
          planId: row.plan_id,
          producerJobId: row.producer_job_id,
        });
        if (artifact === null) continue;
        opened.store.completeCandidateHeadProducer({
          projectId: opened.projectId,
          producerJobId: row.producer_job_id,
          processBootId: row.process_boot_id,
          ownerPid: row.owner_pid,
          packet: artifact.packet,
        });
      } catch {
        // Recovery below converts ambiguous external starts to UNKNOWN.
      }
    }
  };
  if (headProducerEnabled) {
    try {
      reconcilePriorHeadArtifacts();
      opened.store.recoverCandidateHeadProducers({
        projectId: opened.projectId,
        currentProcessBootId: CANDIDATE_PROCESS_BOOT_ID,
        isProcessAlive,
      });
      headProducerReady = true;
    } catch {
      headProducerReady = false;
    }
  }
  const headProviderGateOpen = () => {
    if (
      !headProducerEnabled ||
      !headProducerReady ||
      runtimeAccountingBlocked
    ) {
      return false;
    }
    const budget = productionProjectBudgetSnapshot(
      opened.store,
      opened.projectId,
      projectCeilingNanoUsd,
    );
    if (
      !budget.aggregatesConsistent ||
      (budget.configured && (!budget.policyMatches || !budget.ceilingMatches)) ||
      budget.unknown > 0 ||
      BigInt(budget.spent) + BigInt(budget.reserved) + 1n >
        BigInt(budget.ceiling)
    ) {
      return false;
    }
    return (
      productionUnavailableCircuitCount(
        opened.paths.projectRoot,
        primaryProfile,
        now(),
      ) === 0
    );
  };
  const preStartHeadFailurePacket = (error) => {
    const summary = safeDiagnosticText(error);
    return Object.freeze({
      schema_version: 1,
      result_protocol: 3,
      status: "FAIL",
      execution_status: "CONTRACT_ERROR",
      evidence_verdict: "UNRESOLVED",
      cache_hit: false,
      summary,
      positive_findings: [],
      negative_findings: [summary],
      residual_risks: [
        "The Sol runner did not cross the durable external-start boundary.",
      ],
      recommended_next_action:
        "Repair the local producer contract before submitting another head.",
      scientific_uncertainty: false,
      architecture_uncertainty: true,
      scope_deviation: false,
    });
  };
  const runHeadQueueUntilIdle = async () => {
    while (!stopping && headProviderGateOpen()) {
      const producer = opened.store.listQueuedCandidateHeadProducers({
        projectId: opened.projectId,
        limit: 1,
      })[0];
      if (producer === undefined) return;
      const runtimeRecord = headRuntimeForProducer(producer);
      opened.store.claimCandidateHeadProducer({
        projectId: opened.projectId,
        producerJobId: producer.producerJobId,
        processBootId: CANDIDATE_PROCESS_BOOT_ID,
        ownerPid: process.pid,
      });
      try {
        await runtimeRecord.manager.runPlannedJob(producer.planId, {
          jobId: producer.producerJobId,
          beforeExternalStart() {
            opened.store.markCandidateHeadProducerStarted({
              projectId: opened.projectId,
              producerJobId: producer.producerJobId,
              processBootId: CANDIDATE_PROCESS_BOOT_ID,
              ownerPid: process.pid,
            });
          },
        });
        const artifact = exactHeadTerminalArtifact(producer);
        if (artifact === null) {
          throw new Error("candidate Sol runner returned no terminal artifact");
        }
        opened.store.completeCandidateHeadProducer({
          projectId: opened.projectId,
          producerJobId: producer.producerJobId,
          processBootId: CANDIDATE_PROCESS_BOOT_ID,
          ownerPid: process.pid,
          packet: artifact.packet,
        });
      } catch (error) {
        const state = opened.store.database
          .prepare(
            `SELECT producer_state,external_start_possible
             FROM head_producer_attempts
             WHERE project_id=? AND producer_job_id=?`,
          )
          .get(opened.projectId, producer.producerJobId);
        if (
          state?.producer_state === "RUNNING" &&
          state.external_start_possible === 1
        ) {
          opened.store.markCandidateHeadProducerUnknown({
            projectId: opened.projectId,
            producerJobId: producer.producerJobId,
            reasonCode: "head-pump-failed-after-external-start",
          });
        } else if (state?.producer_state === "CLAIMED") {
          opened.store.completeCandidateHeadProducer({
            projectId: opened.projectId,
            producerJobId: producer.producerJobId,
            processBootId: CANDIDATE_PROCESS_BOOT_ID,
            ownerPid: process.pid,
            packet: preStartHeadFailurePacket(error),
          });
        } else if (
          ![
            "SUCCEEDED",
            "FAILED",
            "BLOCKED",
            "UNKNOWN",
            "CANCELED",
          ].includes(state?.producer_state)
        ) {
          throw error;
        }
      }
    }
  };
  scheduleHeadPump = () => {
    if (!headProducerEnabled || !headProducerReady || stopping) {
      return Promise.resolve();
    }
    if (headPumpPromise !== null) return headPumpPromise;
    headPumpPromise = runHeadQueueUntilIdle()
      .catch((error) => {
        headProducerReady = false;
        throw error;
      })
      .finally(() => {
        headPumpPromise = null;
        if (
          !stopping &&
          headProducerReady &&
          headProviderGateOpen() &&
          opened.store.listQueuedCandidateHeadProducers({
            projectId: opened.projectId,
            limit: 1,
          }).length > 0
        ) {
          queueMicrotask(() => void scheduleHeadPump().catch(() => {}));
        }
      });
    return headPumpPromise;
  };
  const daemon = createCandidateOrchestratorDaemonV2({
    projectId: opened.projectId,
    store: opened.store,
    secret,
    capabilityVerifier(claim) {
      if (claim.projectId !== opened.projectId) return false;
      opened.store.registerCandidateOrigin(claim);
      return true;
    },
    legacyValidators,
    migrationAttestation: opened.migrationAttestation,
    cancelWhenUnobserved: true,
    async onProducerCancelled(context) {
      if (context.kind === "WORKER") {
        runtime?.abortCancelled();
        return;
      }
      const producer = opened.store.database
        .prepare(
          `SELECT producer.producer_job_id,producer.plan_id
           FROM head_claims AS claim
           JOIN head_producer_attempts AS producer
             ON producer.head_run_id=claim.head_run_id
            AND producer.project_id=claim.project_id
           WHERE claim.project_id=? AND claim.public_id=?`,
        )
        .get(opened.projectId, context.publicJobId);
      if (producer === undefined) return;
      const runtimeRecord = headRuntimeForProducer({
        planId: producer.plan_id,
        producerJobId: producer.producer_job_id,
      });
      runtimeRecord.manager.cancel(producer.producer_job_id);
    },
    rpcHandlers: {
      ...headRpcHandlers,
      workerSubmit({ api, payload, session }) {
        if (runtimeAccountingBlocked) {
          const error = new Error("daemon activation is disabled");
          error.code = "ACTIVATION_DISABLED";
          throw error;
        }
        const validated = assertProductionWorkerSubmission(
          payload.input,
          payload.mode,
          primaryProfile,
        );
        const contract = createProductionWorkerEnvelope(
          payload.input,
          payload.mode,
          session,
          validated,
        );
        const submitted = api.submit({ contract });
        queueMicrotask(() => void pump().catch(() => {}));
        return submitted;
      },
      health({ api, session }) {
        return buildProductionCandidateHealth({
          api,
          session,
          migrationAttestation: opened.migrationAttestation,
          store: opened.store,
          storeRoot: opened.paths.baseStoreRoot,
          projectRoot: opened.paths.projectRoot,
          projectCeilingNanoUsd,
          primaryProfile,
          readerPoolPolicy: exactReaderPoolPolicy,
          headReadiness: Object.freeze({
            validatorActive: headValidatorActive,
            producerActive: headProducerReady,
          }),
          nowMs: now(),
        });
      },
    },
    handshakeTimeoutMs: 5_000,
    requestTimeoutMs: 5_000,
    maxConnections: 16,
  });
  let stopped = false;
  return Object.freeze({
    address: daemon.address,
    projectId: opened.projectId,
    async start() {
      const started = await daemon.start();
      if (headProducerEnabled && headProducerReady) {
        queueMicrotask(() => void scheduleHeadPump().catch(() => {}));
      }
      return started;
    },
    async stop() {
      if (stopped) return;
      stopped = true;
      stopping = true;
      await daemon.stop();
      for (const runtimeRecord of headRuntimes.values()) {
        runtimeRecord.manager.cancelAll();
      }
      await Promise.allSettled(
        [pumpPromise, headPumpPromise].filter(Boolean),
      );
      opened.store.close();
    },
  });
}

export function resolveProductionDaemonClientContext({
  storeRoot = defaultStoreRoot(),
  projectId = process.env.DEEPLUNA_PROJECT_ID,
  workspace = process.cwd(),
  originThreadId = process.env.CODEX_THREAD_ID,
} = {}) {
  const workspaceRoot = realpathSync(path.resolve(workspace));
  const exactProjectId = resolveProjectId(projectId, workspaceRoot);
  const paths = productionDaemonPaths(storeRoot, exactProjectId);
  const projectSecret = ensureProjectSecret(paths.projectRoot);
  const origin = deriveOriginContext(
    originThreadId ?? `local-${process.pid}`,
    projectSecret,
  );
  return Object.freeze({
    ...paths,
    projectId: exactProjectId,
    workspaceRoot,
    origin,
    secret: Buffer.from(projectSecret, "hex"),
  });
}

export async function connectProductionCandidateDaemon(options = {}) {
  const context = resolveProductionDaemonClientContext(options);
  const primaryProfile = resolvePrimaryProfile();
  const legacyValidators = createProductionLegacyValidators(primaryProfile, {
    projectId: context.projectId,
    projectScope: "project",
    allowedRoots: [context.workspaceRoot],
  });
  const client = await connectCandidateDaemonClientV2({
    projectId: context.projectId,
    secret: context.secret,
    originThreadHash: context.origin.originThreadHash,
    originCapabilityHash: context.origin.originCapabilityHash,
    legacyValidators,
    timeoutMs: 5_000,
  });
  const request = (method, payload, requestOptions) => {
    if (method === "worker.submit") {
      assertProductionWorkerSubmission(
        payload?.input,
        payload?.mode,
        primaryProfile,
      );
    }
    return client.request(method, payload, requestOptions);
  };
  return Object.freeze({
    address: client.address,
    originId: client.originId,
    runtimeBuildHash: client.runtimeBuildHash,
    serverInstanceId: client.serverInstanceId,
    serverStartedAtMs: client.serverStartedAtMs,
    context,
    request,
    close: client.close,
  });
}

const routeConstraintsInput = z.object({
  allowed_routes: z.array(
    z.enum([
      "LOCAL", "FLASH", "DIRECT_PRO", "V4_PRO", "NEMOTRON", "GLM", "LUNA", "SOL",
    ]),
  ).min(1),
  fallback_policy: z.enum(["NO_LUNA", "LUNA_ELIGIBLE"]),
  maximum_attempts: z.number().int().min(1).max(3),
  maximum_estimated_cost_usd: z.number().min(0),
  privacy_class: z.enum(["LOCAL_ONLY", "PROVIDER_ALLOWED"]),
  maximum_provider_calls: z.number().int().min(1).max(MAX_TOOL_TURNS)
    .describe("Maximum provider HTTP calls for this local worker run; default 2."),
  maximum_input_tokens: z.number().int().min(1).max(Number.MAX_SAFE_INTEGER)
    .describe("Maximum aggregate input tokens for the route contract."),
  maximum_cached_input_tokens: z.number().int().min(1).max(Number.MAX_SAFE_INTEGER)
    .describe("Maximum cached-input subset of maximum_input_tokens."),
  maximum_output_tokens_total: z.number().int().min(1).max(Number.MAX_SAFE_INTEGER)
    .describe("Maximum aggregate output tokens; max_output_tokens remains per call."),
  maximum_total_tokens: z.number().int().min(1).max(Number.MAX_SAFE_INTEGER)
    .describe("Maximum aggregate input plus output tokens."),
}).strict().partial().superRefine((value, context) => {
  try {
    normalizeRouteConstraints(value);
  } catch (error) {
    context.addIssue({
      code: "custom",
      message: error instanceof Error ? error.message : String(error),
    });
  }
});

const commonInput = {
  task_id: z.string().max(64).optional(),
  objective: z.string().min(1).max(12_000),
  tier: z.enum(["FLASH", "PRO", "REASONING"]).optional(),
  workspace: z.string().optional(),
  allowed_paths: z.array(
    z.string().describe(
      "Workspace-relative file or directory path; absolute paths are rejected.",
    ),
  ).default([]),
  required_reads: z.array(z.object({
    path: z.string().min(1).describe(
      "Workspace-relative evidence file path; absolute paths are rejected.",
    ),
    unit: z.literal("line"),
    start: z.number().int().min(1),
    end: z.number().int().min(1).nullable(),
  }).strict()).default([]),
  coverage_spec: z.object({
    mode: z.literal("ALL_REQUIRED_READS"),
    citations_required_for: z.array(z.enum([
      "positive_findings",
      "negative_findings",
    ])).max(2),
  }).strict().optional(),
  forbidden_actions: z.array(z.string()).default([]),
  commands_tests: z.array(z.string()).default([]),
  local_assertions: z.array(z.object({
    command_index: z.number().int().min(0),
    stream: z.enum(["stdout", "stderr"]),
    pattern: z.string().min(1).max(MAX_LOCAL_ASSERTION_PATTERN_CHARS),
    must_match: z.boolean(),
  }).strict()).max(MAX_LOCAL_ASSERTIONS).optional(),
  write_verifications: z.array(z.object({
    path: z.string().min(1),
    sha256: z.string().regex(/^[a-f0-9]{64}$/),
    byte_length: z.number().int().min(0).max(MAX_WRITE_VERIFICATION_BYTES),
    content_base64: z.string().max(MAX_LOCAL_EXACT_WRITE_BASE64_CHARS),
  }).strict()).max(MAX_WRITE_VERIFICATIONS).optional(),
  frozen_artifacts: z.array(z.object({
    artifact_id: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/),
    path: z.string().min(1),
    sha256: z.string().regex(/^[a-f0-9]{64}$/),
    byte_length: z.number().int().min(0).max(MAX_FROZEN_ARTIFACT_BYTES),
    content_base64: z.string().max(MAX_FROZEN_ARTIFACT_BASE64_CHARS),
  }).strict()).max(MAX_FROZEN_ARTIFACTS).optional().describe(
    "Bounded Flash WRITE-only private payload table. Providers receive only descriptors " +
      "and may reference bytes with strict write_frozen_file operations.",
  ),
  definition_of_done: z.array(z.string()).min(1),
  required_output: z.array(z.string()).min(1),
  timeout_minutes: z.number().min(1).max(180).optional(),
  max_output_tokens: z.number()
    .int()
    .min(MIN_LOCAL_OUTPUT_TOKENS)
    .max(8_192)
    .optional()
    .describe(OUTPUT_TOKEN_BOUNDS_DESCRIPTION),
  reuse_cache: z.boolean().optional(),
  require_cache: z.boolean().optional(),
  route_constraints: routeConstraintsInput.optional(),
};

const batchInput = {
  concurrency: z.union([z.literal(1), z.literal(2)]).default(1),
  tasks: z.array(z.object({
    node_id: z.string().min(1).max(64),
    depends_on: z.array(z.string().min(1).max(64)).default([]),
    accepted_evidence_verdicts: z.array(z.enum([
      "POSITIVE",
      "NEGATIVE",
      "NULL",
      "MIXED",
      "NOT_APPLICABLE",
    ])).min(1).optional(),
    ...commonInput,
  })).min(1).max(20),
};

const daemonBatchInput = {
  ...batchInput,
  concurrency: z.number().int().min(1).max(20).default(1),
};

const solRouteInput = {
  ...commonInput,
  tier: z.literal("FLASH").optional(),
  authority_domains: z.array(z.enum(SOL_AUTHORITY_DOMAINS)).default([]),
  complexity: z.number().int().min(0).max(3),
  scientific_claim_risk: z.number().int().min(0).max(3),
  ambiguity: z.number().int().min(0).max(3),
  blast_radius: z.number().int().min(0).max(3),
  oracle_weakness: z.number().int().min(0).max(3),
  value_at_risk: z.number().int().min(0).max(3),
  mechanical: z.boolean().default(false),
  deterministic_oracle: z.boolean().default(false),
  estimated_work_units: z.number().int().min(1).max(1_000),
  current_effort: z.enum(SOL_HEAD.efforts).default("xhigh"),
  xhigh_impasse: z.object({
    attempt_fingerprint: z.string().max(256),
    alternatives: z.array(z.string().max(500)).max(8),
    conflicting_evidence_lanes: z.array(z.string().max(500)).max(8),
    material_consequence: z.boolean(),
    cheaper_resolution_exhausted: z.boolean(),
    prior_max_attempt: z.boolean(),
  }).strict().optional(),
};

const solRouteInputSchema = z.object(solRouteInput).strict();

export function validateSolRoutePlanInput(input, {
  projectId,
  projectScope = "project",
  allowedRoots = null,
  primaryProfile = resolvePrimaryProfile(),
} = {}) {
  const parsed = solRouteInputSchema.parse(input);
  if (parsed.tier !== undefined && parsed.tier !== "FLASH") {
    throw new Error("Sol route plans are READ_ONLY and require the FLASH tier");
  }
  if (
    Array.isArray(parsed.write_verifications) &&
    parsed.write_verifications.length > 0
  ) {
    throw new Error("Sol route plans are READ_ONLY and reject write verifications");
  }
  const task = validateSubmission(
    { ...parsed, tier: "FLASH" },
    "READ_ONLY",
    primaryProfile,
    { codexOrchestrationEnabled: true },
  );
  const roots = allowedRoots === null || allowedRoots === undefined
    ? []
    : allowedRoots;
  if (!Array.isArray(roots)) {
    throw new TypeError("allowedRoots must be an array when provided");
  }
  const canonicalRoots = roots.map((root) => {
    const resolved = path.resolve(String(root ?? ""));
    if (!existsSync(resolved) || !statSync(resolved).isDirectory()) {
      throw new Error(`allowed root is not a directory: ${resolved}`);
    }
    return realpathSync(resolved);
  });
  if (
    canonicalRoots.length > 0 &&
    !canonicalRoots.some((root) => isWithin(root, task.workspace))
  ) {
    throw new Error(`workspace is outside the authenticated project roots: ${task.workspace}`);
  }
  const exactProjectId = projectId === undefined
    ? null
    : resolveProjectId(projectId, task.workspace);
  const exactProjectScope = resolveProjectScope(projectScope);
  const normalizedInput = Object.freeze({
    ...parsed,
    tier: "FLASH",
  });
  const route = classifySolRoute(normalizedInput);
  return Object.freeze({
    input: normalizedInput,
    task,
    route,
    routeContract: Object.freeze(buildSolRouteContract(normalizedInput, route)),
    projectId: exactProjectId,
    projectScope: exactProjectScope,
    allowedRoots: Object.freeze(canonicalRoots),
    providerCalls: 0,
  });
}

function toolResponse(value) {
  return {
    content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
    structuredContent: value,
  };
}

const deepseekHealthOutputSchema = z.object({
  schema_version: z.number().int().positive(),
  readiness: z.enum(["READY", "DEGRADED", "BLOCKED"]),
  reason_codes: z.array(z.string()),
  circuits: z.object({
    provider_calls_enabled: z.boolean(),
  }).passthrough(),
}).passthrough();

function normalizeDeepseekHealthResult(value) {
  const parsed = deepseekHealthOutputSchema.safeParse(value);
  if (parsed.success) {
    return value;
  }
  return {
    schema_version: 1,
    readiness: "BLOCKED",
    reason_codes: ["invalid-health-contract"],
    circuits: {
      provider_calls_enabled: false,
    },
  };
}

function requireDaemonClient(client) {
  if (
    !client ||
    typeof client !== "object" ||
    typeof client.request !== "function" ||
    typeof client.close !== "function"
  ) {
    throw new TypeError("daemon client must provide request(type, payload) and close()");
  }
  return client;
}

export class DaemonJobManagerProxy {
  constructor(client, {
    primaryProfile = resolvePrimaryProfile(),
    codexOrchestrationEnabled = resolveCodexOrchestrationEnabled(),
    readerPoolPolicy = resolveFastReaderPoolPolicy(),
  } = {}) {
    this.client = requireDaemonClient(client);
    this.primaryProfile = primaryProfile;
    this.codexOrchestrationEnabled = codexOrchestrationEnabled;
    this.readerPoolPolicy = resolveFastReaderPoolPolicy(readerPoolPolicy);
    this.daemonBacked = true;
    this.daemonContext = client.context ?? null;
    if (this.daemonContext !== null) {
      this.baseStoreRoot = this.daemonContext.baseStoreRoot;
      this.storeRoot = this.daemonContext.baseStoreRoot;
      this.projectId = this.daemonContext.projectId;
      this.projectRoot = this.daemonContext.projectRoot;
      this.origin = this.daemonContext.origin;
      this.batchesRoot = path.join(this.projectRoot, "batches");
      this.retentionDays = Number(process.env.DEEPLUNA_RETENTION_DAYS) || 30;
      this.nowFunction = Date.now;
      this.apiKey = "";
    }
  }

  async submit(input, mode) {
    return this.client.request("worker.submit", { input, mode });
  }

  async status(jobId) {
    return this.client.request("job.status", { jobId });
  }

  async cancel(jobId) {
    return this.client.request("job.cancel", { jobId });
  }

  async metrics() {
    const metrics = await this.client.request("metrics", {});
    if (this.daemonContext === null) return metrics;
    const health = await this.client.request("health", {});
    const budget = health.budget;
    const cumulativeBudgetSafe =
      BigInt(budget.spent_nano_usd) +
        BigInt(budget.open_reserved_nano_usd) +
        BigInt(budget.next_call_estimate_nano_usd) <=
        BigInt(budget.project_ceiling_nano_usd) &&
      budget.unknown_reservations === 0;
    return {
      process_name: this.primaryProfile.displayName,
      version: VERSION,
      cumulative_budget_safe: cumulativeBudgetSafe,
      daemon_active: true,
      check_dl: health,
      active_primary_profile: this.primaryProfile.id,
      jobs: {
        total: metrics.total_jobs,
        statuses: {
          QUEUED: metrics.queued_jobs,
          RUNNING: metrics.running_jobs + metrics.validating_jobs,
          TERMINAL: metrics.terminal_jobs,
        },
        cache_hits: 0,
      },
      cache: {
        entries: 0,
        bytes: 0,
        retention_days: this.retentionDays,
        max_bytes: Number(process.env.DEEPLUNA_CACHE_MAX_BYTES) || 256 * 1024 * 1024,
      },
      providers: {
        primary: {
          profile_id: this.primaryProfile.id,
          provider: this.primaryProfile.provider,
          route: this.primaryProfile.route,
          model: this.primaryProfile.models.FLASH,
          service_tier: this.primaryProfile.serviceTier,
          runs: metrics.provider_transmissions,
          api_calls: metrics.provider_transmissions,
          prompt_tokens: metrics.input_tokens,
          completion_tokens: metrics.output_tokens,
          total_tokens: metrics.total_tokens,
          prompt_cache_hit_tokens: metrics.cached_input_tokens,
          prompt_cache_miss_tokens:
            metrics.input_tokens - metrics.cached_input_tokens,
        },
        luna: {
          runs: 0,
          elapsed_ms: 0,
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        },
        glm: {
          runs: 0,
          elapsed_ms: 0,
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        },
        local: { runs: 0, commands: 0, writes: 0, failures: 0 },
      },
    };
  }

  async check() {
    const health = await this.client.request("health", {});
    if (health?.capacity?.read_limit !== this.readerPoolPolicy.readLimit) {
      throw new Error(
        "daemon Fast reader limit does not match the authenticated client policy",
      );
    }
    return health;
  }
}

export class DaemonBatchManagerProxy {
  constructor(client) {
    this.client = requireDaemonClient(client);
    this.daemonBacked = true;
  }

  async submit(input) {
    return this.client.request("batch.submit", { input });
  }

  async status(batchId) {
    return this.client.request("batch.status", { batchId });
  }

  async metrics() {
    return this.client.request("batch.metrics", {});
  }
}

export class DaemonHeadManagerProxy {
  constructor(client) {
    this.client = requireDaemonClient(client);
    this.daemonBacked = true;
  }

  async plan(input) {
    return this.client.request("head.plan", { input });
  }

  async submit(planId) {
    return this.client.request("head.submit", { planId });
  }

  async status(jobId) {
    return this.client.request("head.status", { jobId });
  }

  async cancel(jobId) {
    return this.client.request("head.cancel", { jobId });
  }

  async metrics() {
    return this.client.request("head.metrics", {});
  }
}

export const DAEMON_RUNTIME_ACCEPTED = CANDIDATE_DAEMON_RUNTIME_ACCEPTED;

export function selectRuntimeMode({
  embeddedCompat = process.env.DEEPLUNA_EMBEDDED_COMPAT,
  daemonAccepted = DAEMON_RUNTIME_ACCEPTED,
} = {}) {
  if (typeof daemonAccepted !== "boolean") {
    throw new TypeError("daemonAccepted must be boolean");
  }
  if (!daemonAccepted) return "EMBEDDED";
  if (embeddedCompat === undefined || embeddedCompat === "") return "DAEMON";
  if (embeddedCompat === "1") return "EMBEDDED";
  throw new Error("DEEPLUNA_EMBEDDED_COMPAT must be unset or exactly 1");
}

export function createEmbeddedRuntimeManagers() {
  const manager = new JobManager();
  const headManager = manager.codexOrchestrationEnabled
    ? new HeadJobManager({
        storeRoot: manager.baseStoreRoot ?? manager.storeRoot,
        projectId: manager.projectId,
        originContext: manager.origin,
        budgetController: manager.budgetController,
      })
    : null;
  return Object.freeze({
    mode: "EMBEDDED",
    manager,
    batchManager: null,
    headManager,
    client: null,
  });
}

export async function createRuntimeManagers({
  embeddedCompat = process.env.DEEPLUNA_EMBEDDED_COMPAT,
  daemonAccepted = DAEMON_RUNTIME_ACCEPTED,
  createEmbedded = createEmbeddedRuntimeManagers,
  connectDaemon = connectProductionCandidateDaemon,
} = {}) {
  const mode = selectRuntimeMode({ embeddedCompat, daemonAccepted });
  if (mode === "EMBEDDED") {
    if (typeof createEmbedded !== "function") {
      throw new TypeError("embedded runtime factory must be a function");
    }
    const runtime = await createEmbedded();
    if (!runtime || typeof runtime !== "object" || !runtime.manager) {
      throw new TypeError("embedded runtime factory returned an invalid runtime");
    }
    return Object.freeze({
      ...runtime,
      mode,
      batchManager: runtime.batchManager ?? null,
      headManager: runtime.headManager ?? null,
      client: runtime.client ?? null,
    });
  }
  if (typeof connectDaemon !== "function") {
    throw new Error("daemon runtime selected without an injected connector");
  }
  const client = requireDaemonClient(await connectDaemon());
  const manager = new DaemonJobManagerProxy(client);
  return Object.freeze({
    mode,
    manager,
    batchManager: new BatchManager(manager),
    headManager: new DaemonHeadManagerProxy(client),
    client,
  });
}

export function createStdinShutdownHandler({
  daemonBacked,
  client = null,
  manager,
  headManager = null,
  server,
}) {
  if (!server || typeof server.close !== "function") {
    throw new TypeError("MCP server must provide close()");
  }
  let shutdownPromise = null;
  return function shutdown() {
    shutdownPromise ??= (async () => {
      try {
        if (daemonBacked) {
          if (!client || typeof client.close !== "function") {
            throw new TypeError("daemon client must provide close()");
          }
          await client.close();
        } else {
          await manager?.cancelAll?.();
          await headManager?.cancelAll?.();
        }
      } finally {
        await server.close();
      }
    })();
    return shutdownPromise;
  };
}

export function createMcpServer(
  manager = new JobManager(),
  batchManager = null,
  headManager = null,
) {
  const profile = manager.primaryProfile ?? resolvePrimaryProfile();
  const fastProfile = profile.id === "deepinfra-fast";
  const readerPoolPolicy = resolveFastReaderPoolPolicy();
  const codexOrchestrationEnabled = manager.codexOrchestrationEnabled !== false;
  const primaryLabel = fastProfile
    ? "DeepSeek V4 Flash on DeepInfra Priority"
    : "DeepSeek Flash or Pro";
  const nonFastTierGuidance = fastProfile
    ? "Pro uses DeepSeek V4 Pro and remains the default; explicit Reasoning uses Nemotron Ultra."
    : "Pro and Reasoning use DeepSeek V4 Pro.";
  const hostLogBoundary =
    "Codex Desktop TRACE SQLite logs_2.sqlite is external to this bridge and must not be queried or printed as a credential source.";
  const glmPackedGuidance =
    "Explicit GLM packed evidence jobs must supply exact required_reads and ALL_REQUIRED_READS coverage; the bridge verifies and receipts them locally, then sends one tool-free provider request with a redacted per-stage failure log.";
  const routeCapGuidance =
    "route_constraints exposes maximum_provider_calls, maximum_input_tokens, " +
    "maximum_cached_input_tokens, maximum_output_tokens_total, and maximum_total_tokens; " +
    "max_output_tokens remains the per-call ceiling.";
  if (
    manager.daemonBacked &&
    (
      !batchManager ||
      !headManager ||
      batchManager.daemonBacked !== true ||
      headManager.daemonBacked !== true ||
      batchManager.client !== manager.client ||
      headManager.client !== manager.client
    )
  ) {
    throw new Error(
      "daemon-backed MCP requires an explicit batch scheduler and head proxy sharing one daemon client",
    );
  }
  let resolvedBatchManager = batchManager;
  const batches = () => {
    resolvedBatchManager ??= new BatchManager(manager);
    return resolvedBatchManager;
  };
  let resolvedHeadManager = headManager;
  const heads = () => {
    resolvedHeadManager ??= new HeadJobManager({
      storeRoot: manager.baseStoreRoot ?? manager.storeRoot,
      projectId: manager.projectId,
      originContext: manager.origin,
      budgetController: manager.budgetController,
    });
    return resolvedHeadManager;
  };
  const server = new McpServer(
    { name: "deepluna-orchestrator", version: VERSION },
    {
      instructions:
        codexOrchestrationEnabled
          ? readerPoolPolicy.fastOnly
            ? `${profile.displayName} is the only DeepLuna worker route: ${primaryLabel}, NO_LUNA, with no model fallback. The local adaptive Sol router remains the head and final authority; Sol is not a DeepLuna worker. Sol xhigh retains science, architecture, implementation, and final approval. Keep at most ${readerPoolPolicy.readLimit} isolated Fast worker reads, one exclusive worker WRITE, or one separate Sol head job; poll status and verify every claim locally. Reader-pool mode is ${readerPoolPolicy.mode}. ${hostLogBoundary}`
            : `${profile.displayName} is the canonical cache to ${primaryLabel} to Luna xhigh chain for bounded mechanical work. The local adaptive Sol router may start one isolated read-only Sol head job at medium, high, xhigh, or one-shot Max. Sol xhigh retains science, architecture, implementation, and final approval. Keep at most ${readerPoolPolicy.readLimit} worker reads, one worker WRITE, or one separate Sol head job; poll status and verify every claim locally. ${glmPackedGuidance} ${hostLogBoundary}`
          : `${profile.displayName} is primary-provider-only. Use the local cache and ${primaryLabel}; fail closed when the primary provider is unavailable. Codex GPT, Luna fallback, and Sol-head orchestration are disabled for this server instance. ${hostLogBoundary}`,
    },
  );
  server.registerTool(
    "deepseek_read_submit",
    {
      title: "Submit bounded canonical read work",
      description:
        codexOrchestrationEnabled
          ? `Submit an asynchronous READ_ONLY repository task to ${primaryLabel}, with automatic GPT-5.6 Luna xhigh fallback in the same job when the primary is unavailable. Explicit GLM requires packed required_reads and complete citation coverage. Returns a job ID immediately; poll deepseek_job_status. Exact safe local cache reuse is enabled by default. ${routeCapGuidance}`
          : `Submit an asynchronous READ_ONLY repository task to ${primaryLabel}. The job fails closed when the primary is unavailable; no Codex GPT fallback is permitted. Returns a job ID immediately; poll deepseek_job_status. Exact safe local cache reuse is enabled by default. ${routeCapGuidance}`,
      inputSchema: commonInput,
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: false, openWorldHint: true },
    },
    async (input) => toolResponse(await manager.submit(input, "READ_ONLY")),
  );
  server.registerTool(
    "deepseek_write_submit",
    {
      title: "Submit allowlisted canonical implementation work",
      description:
        readerPoolPolicy.fastOnly
          ? `Submit one asynchronous WRITE task to ${primaryLabel}. Flash is enforced with a one-call FLASH-only NO_LUNA strict write-plan contract, required-read citation coverage, host-staged application, and host post-write verification. Optional bounded frozen_artifacts keep exact task-supplied bytes out of the provider response; the provider may only reference their closed descriptors. Requires explicit allowed_paths and independent local acceptance. ${routeCapGuidance}`
          : codexOrchestrationEnabled
          ? `Submit one asynchronous WRITE task to ${primaryLabel}. ${nonFastTierGuidance} Eligible GPT-5.6 Luna xhigh fallback may run in the same job. Explicit Flash WRITE is accepted only as a one-call FLASH-only NO_LUNA strict write-plan contract with required-read citation coverage, host-staged application, and host post-write verification. Optional bounded frozen_artifacts keep exact task-supplied bytes out of the provider response; the provider may only reference their closed descriptors. Requires explicit allowed_paths. Sol must inspect changed paths and run final acceptance tests before approval. ${routeCapGuidance}`
          : `Submit one asynchronous WRITE task to ${primaryLabel}. ${nonFastTierGuidance} Explicit Flash WRITE is accepted only as a one-call FLASH-only NO_LUNA strict write-plan contract with required-read citation coverage, host-staged application, and host post-write verification. Optional bounded frozen_artifacts keep exact task-supplied bytes out of the provider response; the provider may only reference their closed descriptors. The job fails closed when the primary is unavailable; no Codex GPT fallback is permitted. Requires explicit allowed_paths and independent local acceptance. ${routeCapGuidance}`,
      inputSchema: {
        ...commonInput,
        tier: z.enum(["PRO", "REASONING", "FLASH"]).default(
          readerPoolPolicy.fastOnly ? "FLASH" : "PRO",
        ),
      },
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
    },
    async (input) => toolResponse(await manager.submit(input, "WRITE")),
  );
  if (codexOrchestrationEnabled) {
    server.registerTool(
      "sol_route_plan",
      {
        title: "Plan a deterministic adaptive Sol route",
        description:
          "Validate and fingerprint a bounded READ_ONLY task, then select DeepLuna, current handling, or an isolated Sol medium/high/xhigh/one-shot-Max head job. Planning is local, deterministic, idempotent, and makes zero provider calls.",
        inputSchema: solRouteInput,
        annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      },
      async (input) => toolResponse(await heads().plan(input)),
    );
    server.registerTool(
      "sol_head_submit",
      {
        title: "Submit an eligible isolated Sol head plan",
        description:
          "Start one asynchronous read-only gpt-5.6-sol job at the effort frozen in an existing route plan. Exact cache precedes launch; Max is one shot per exact conflict and never retries automatically.",
        inputSchema: { plan_id: z.string().regex(/^SRP-[a-f0-9]{32}$/) },
        annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: false, openWorldHint: false },
      },
      async ({ plan_id }) => toolResponse(await heads().submit(plan_id)),
    );
  }
  server.registerTool(
    "deepseek_job_status",
    {
      title: codexOrchestrationEnabled
        ? "Read a DeepLuna or Sol head job checkpoint"
        : "Read a primary-provider DeepLuna job checkpoint",
      description: codexOrchestrationEnabled
        ? "Dispatch DS job IDs to DeepLuna and SH job IDs to the isolated Sol head manager, returning bounded status, provenance, usage, and evidence pointers."
        : "Return bounded status, provenance, usage, and evidence pointers for DS job IDs only.",
      inputSchema: { job_id: z.string().min(1) },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    },
    async ({ job_id }) => {
      if (String(job_id).startsWith("SH-") && !codexOrchestrationEnabled) {
        throw new Error("Sol-head job access is disabled for this DeepLuna instance");
      }
      return toolResponse(
        String(job_id).startsWith("SH-")
          ? await heads().status(job_id)
          : await manager.status(job_id),
      );
    },
  );
  server.registerTool(
    "deepseek_job_cancel",
    {
      title: codexOrchestrationEnabled
        ? "Cancel an active DeepLuna or Sol head job"
        : "Cancel an active primary-provider DeepLuna job",
      description: codexOrchestrationEnabled
        ? "Dispatch DS or SH job cancellation and preserve bounded partial evidence without changing the other provider circuit."
        : "Cancel a DS job and preserve bounded partial evidence. SH job access is disabled.",
      inputSchema: { job_id: z.string().min(1) },
      annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: false },
    },
    async ({ job_id }) => {
      if (String(job_id).startsWith("SH-") && !codexOrchestrationEnabled) {
        throw new Error("Sol-head job access is disabled for this DeepLuna instance");
      }
      return toolResponse(
        String(job_id).startsWith("SH-")
          ? await heads().cancel(job_id)
          : await manager.cancel(job_id),
      );
    },
  );
  server.registerTool(
    "deepseek_batch_submit",
    {
      title: "Submit a DeepLuna READ_ONLY evidence DAG",
      description:
        manager.daemonBacked
          ? `Submit 1 to 20 dependency-gated READ_ONLY tasks through a client-lifetime scheduler with local checkpoints. Every worker job is durable and accounted by the daemon, whose ${readerPoolPolicy.readLimit} Fast READ lanes control physical provider capacity in ${readerPoolPolicy.mode} mode. Batch DAG orchestration is not restart-durable and does not use a daemon batch RPC. Descendants run only after every dependency PASSes or is CACHED.`
          : `Submit 1 to 20 dependency-gated READ_ONLY tasks. Physical execution is capped at ${readerPoolPolicy.readLimit} worker reads. Descendants run only after every dependency PASSes or is CACHED.`,
      inputSchema: manager.daemonBacked ? daemonBatchInput : batchInput,
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: false, openWorldHint: true },
    },
    async (input) => toolResponse(await batches().submit(input)),
  );
  server.registerTool(
    "deepseek_batch_status",
    {
      title: "Read a DeepLuna batch evidence manifest",
      description:
        "Return dependency states, lifecycle boundaries, and compact durable worker evidence pointers without repeating task prompts.",
      inputSchema: { batch_id: z.string().min(1) },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    },
    async ({ batch_id }) => toolResponse(await batches().status(batch_id)),
  );
  server.registerTool(
    "deepseek_check",
    {
      title: "Check DeepLuna local readiness",
      description:
        "Run the authenticated provider-free Check DL preflight for daemon, identity, capacity, circuit, migration, cache, and cumulative-budget gates.",
      inputSchema: {},
      outputSchema: deepseekHealthOutputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async () => toolResponse(normalizeDeepseekHealthResult(
      typeof manager.check === "function"
        ? await manager.check()
        : {
            schema_version: 1,
            readiness: "BLOCKED",
            reason_codes: ["daemon-inactive"],
            provider_calls_enabled: false,
          },
    )),
  );
  server.registerTool(
    "deepseek_metrics",
    {
      title: "Read DeepLuna cost and cache metrics",
      description: "Aggregate local cache hits and DeepSeek/Luna usage without returning prompts or repository content.",
      inputSchema: {},
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    },
    async () => {
      const [workerMetrics, batchMetrics, headMetrics] = await Promise.all([
        manager.metrics(),
        batches().metrics(),
        codexOrchestrationEnabled ? heads().metrics() : null,
      ]);
      return toolResponse({
        ...workerMetrics,
        batches: batchMetrics,
        codex_orchestration_enabled: codexOrchestrationEnabled,
        ...(codexOrchestrationEnabled ? { sol_heads: headMetrics } : {}),
      });
    },
  );
  return server;
}

export async function main() {
  const runtime = await createRuntimeManagers();
  const { manager, batchManager, headManager, client } = runtime;
  const server = createMcpServer(manager, batchManager, headManager);
  const transport = new StdioServerTransport();
  const shutdown = createStdinShutdownHandler({
    daemonBacked: runtime.mode === "DAEMON",
    client,
    manager,
    headManager,
    server,
  });
  process.stdin.once("end", () => {
    void shutdown().catch((error) => {
      console.error(safeDiagnosticText(error?.stack ?? String(error), [], 8_000));
    });
  });
  await server.connect(transport);
  console.error(safeDiagnosticText(startupBanner(manager.primaryProfile)));
}

export function resolveDaemonCliOptions({
  argv = process.argv.slice(2),
  environmentProjectId = process.env.DEEPLUNA_PROJECT_ID,
} = {}) {
  if (!Array.isArray(argv) || argv.some((value) => typeof value !== "string")) {
    throw new TypeError("daemon command-line arguments must be strings");
  }
  let rawProjectId;
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--daemon") continue;
    let candidate;
    if (argument === "--project-id") {
      index += 1;
      candidate = argv[index];
      if (candidate === undefined) {
        throw new Error("daemon --project-id requires a value");
      }
    } else if (argument.startsWith("--project-id=")) {
      candidate = argument.slice("--project-id=".length);
    } else {
      throw new Error("unsupported daemon command-line argument");
    }
    if (rawProjectId !== undefined) {
      throw new Error("daemon --project-id may be specified only once");
    }
    rawProjectId = candidate;
  }

  const cliProjectId =
    rawProjectId === undefined ? undefined : resolveProjectId(rawProjectId);
  const rawEnvironmentProjectId = String(environmentProjectId ?? "").trim();
  const exactEnvironmentProjectId =
    rawEnvironmentProjectId === ""
      ? undefined
      : resolveProjectId(rawEnvironmentProjectId);
  if (
    cliProjectId !== undefined &&
    exactEnvironmentProjectId !== undefined &&
    cliProjectId !== exactEnvironmentProjectId
  ) {
    throw new Error("daemon project identity conflicts with the environment");
  }
  return Object.freeze({
    projectId: cliProjectId ?? exactEnvironmentProjectId,
  });
}

export async function daemonMain(options = {}) {
  const daemonOptions = resolveDaemonCliOptions(options);
  const daemon = await createProductionCandidateDaemon(daemonOptions);
  await daemon.start();
  console.error(
    safeDiagnosticText(
      `DeepLuna daemon ${CANDIDATE_DAEMON_RELEASE} READY candidate listening on ${daemon.address}`,
      [],
      8_000,
    ),
  );
  let shutdownPromise = null;
  const shutdown = () => {
    shutdownPromise ??= daemon.stop();
    return shutdownPromise;
  };
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.once(signal, () => {
      void shutdown().finally(() => process.exit(0));
    });
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const entry = process.argv.includes("--daemon") ? daemonMain : main;
  entry().catch((error) => {
    console.error(safeDiagnosticText(error?.stack ?? String(error), [], 8_000));
    process.exit(1);
  });
}
