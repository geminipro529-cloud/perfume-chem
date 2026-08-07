import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Tokenizer } from "@huggingface/tokenizers";

export const DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY = Object.freeze({
  model: "deepseek-ai/DeepSeek-V4-Flash-0731",
  revision: "60d8d70770c6776ff598c94bb586a859a38244f1",
  package: "@huggingface/tokenizers",
  package_version: "0.1.3",
  tokenizer_artifact_sha256:
    "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf",
  tokenizer_config_sha256:
    "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547",
  encoding_artifact_sha256:
    "bdbd57c132a1b3725042323d02b98b9d1df28e5f388f134399555d041f5055e0",
});

export const DEEPSEEK_V4_FLASH_TOKEN_MARGIN = Object.freeze({
  basis_points: 500,
  fixed_tokens: 64,
});

const RUNTIME_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const ARTIFACT_ROOT = path.join(
  RUNTIME_ROOT,
  "vendor",
  "deepseek-v4-flash",
  DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.revision,
);
const EXPECTED_MODEL_MAX_LENGTH = 1_048_576;
const CONSERVATIVE_FALLBACK_TOKENS_PER_BYTE = 4;
let verifiedTokenizer = null;

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function readVerifiedJson(filename, expectedHash) {
  const bytes = readFileSync(filename);
  if (sha256(bytes) !== expectedHash) {
    throw new Error("pinned tokenizer artifact identity mismatch");
  }
  const parsed = JSON.parse(bytes.toString("utf8"));
  if (
    parsed === null ||
    typeof parsed !== "object" ||
    Array.isArray(parsed)
  ) {
    throw new Error("pinned tokenizer artifact is malformed");
  }
  return parsed;
}

function loadVerifiedTokenizer(artifactRoot = ARTIFACT_ROOT) {
  if (artifactRoot === ARTIFACT_ROOT && verifiedTokenizer !== null) {
    return verifiedTokenizer;
  }
  const tokenizerJson = readVerifiedJson(
    path.join(artifactRoot, "tokenizer.json"),
    DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.tokenizer_artifact_sha256,
  );
  const tokenizerConfig = readVerifiedJson(
    path.join(artifactRoot, "tokenizer_config.json"),
    DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.tokenizer_config_sha256,
  );
  const encodingBytes = readFileSync(
    path.join(artifactRoot, "encoding", "encoding_dsv4.py"),
  );
  if (
    sha256(encodingBytes) !==
    DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.encoding_artifact_sha256
  ) {
    throw new Error("pinned tokenizer encoding identity mismatch");
  }
  if (tokenizerConfig.model_max_length !== EXPECTED_MODEL_MAX_LENGTH) {
    throw new Error("pinned tokenizer model length identity mismatch");
  }
  const packageJson = JSON.parse(
    readFileSync(
      path.join(
        RUNTIME_ROOT,
        "node_modules",
        "@huggingface",
        "tokenizers",
        "package.json",
      ),
      "utf8",
    ),
  );
  if (
    packageJson.name !== DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.package ||
    packageJson.version !==
      DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.package_version
  ) {
    throw new Error("pinned tokenizer package identity mismatch");
  }
  const loaded = new Tokenizer(tokenizerJson, tokenizerConfig);
  if (artifactRoot === ARTIFACT_ROOT) verifiedTokenizer = loaded;
  return loaded;
}

function renderDeepSeekV4FlashMessages(messages) {
  if (
    !Array.isArray(messages) ||
    messages.length !== 3 ||
    messages[0]?.role !== "system" ||
    messages[1]?.role !== "user" ||
    messages[2]?.role !== "user" ||
    messages.some((message) => typeof message?.content !== "string")
  ) {
    throw new Error("unsupported DeepSeek V4 Flash message shape");
  }
  return [
    "<\uFF5Cbegin\u2581of\u2581sentence\uFF5C>",
    messages[0].content,
    "<\uFF5CUser\uFF5C>",
    messages[1].content,
    "\n\n",
    messages[2].content,
    "<\uFF5CAssistant\uFF5C></think>",
  ].join("");
}

function conservativeFailure(serializedBody, reason) {
  const requestBodyBytes = Buffer.byteLength(serializedBody, "utf8");
  return Object.freeze({
    tokenizer_status: "FAILED_CLOSED",
    tokenizer_failure_reason: String(reason ?? "tokenizer unavailable").slice(0, 256),
    tokenized_prompt_tokens: null,
    constraint_schema_tokens: null,
    tokenizer_margin_basis_points:
      DEEPSEEK_V4_FLASH_TOKEN_MARGIN.basis_points,
    tokenizer_margin_fixed_tokens:
      DEEPSEEK_V4_FLASH_TOKEN_MARGIN.fixed_tokens,
    tokenizer_margin_tokens: null,
    estimated_input_tokens:
      requestBodyBytes * CONSERVATIVE_FALLBACK_TOKENS_PER_BYTE,
    ...DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY,
  });
}

export function estimateDeepSeekV4FlashPrompt(
  canonicalRequest,
  serializedBody,
  { artifactRoot = ARTIFACT_ROOT } = {},
) {
  try {
    if (
      canonicalRequest === null ||
      typeof canonicalRequest !== "object" ||
      Array.isArray(canonicalRequest) ||
      ![
        DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY.model,
        "deepseek-v4-flash",
      ].includes(canonicalRequest.model) ||
      JSON.stringify(canonicalRequest) !== serializedBody
    ) {
      throw new Error("canonical Flash request identity is invalid");
    }
    const tokenizer = loadVerifiedTokenizer(artifactRoot);
    const rendered = renderDeepSeekV4FlashMessages(canonicalRequest.messages);
    const tokenizedPromptTokens = tokenizer.encode(rendered, {
      add_special_tokens: true,
    }).ids.length;
    const constraintSchemaTokens = tokenizer.encode(
      JSON.stringify(canonicalRequest.response_format ?? null),
      { add_special_tokens: false },
    ).ids.length;
    if (
      !Number.isSafeInteger(tokenizedPromptTokens) ||
      tokenizedPromptTokens < 1 ||
      !Number.isSafeInteger(constraintSchemaTokens) ||
      constraintSchemaTokens < 1
    ) {
      throw new Error("pinned tokenizer returned an invalid token count");
    }
    const proportionalMargin = Math.ceil(
      (tokenizedPromptTokens *
        DEEPSEEK_V4_FLASH_TOKEN_MARGIN.basis_points) /
        10_000,
    );
    const tokenizerMarginTokens =
      proportionalMargin + DEEPSEEK_V4_FLASH_TOKEN_MARGIN.fixed_tokens;
    return Object.freeze({
      tokenizer_status: "VERIFIED",
      tokenizer_failure_reason: null,
      tokenized_prompt_tokens: tokenizedPromptTokens,
      constraint_schema_tokens: constraintSchemaTokens,
      tokenizer_margin_basis_points:
        DEEPSEEK_V4_FLASH_TOKEN_MARGIN.basis_points,
      tokenizer_margin_fixed_tokens:
        DEEPSEEK_V4_FLASH_TOKEN_MARGIN.fixed_tokens,
      tokenizer_margin_tokens: tokenizerMarginTokens,
      estimated_input_tokens:
        tokenizedPromptTokens + tokenizerMarginTokens,
      ...DEEPSEEK_V4_FLASH_TOKENIZER_IDENTITY,
    });
  } catch (error) {
    return conservativeFailure(serializedBody, error?.message);
  }
}
