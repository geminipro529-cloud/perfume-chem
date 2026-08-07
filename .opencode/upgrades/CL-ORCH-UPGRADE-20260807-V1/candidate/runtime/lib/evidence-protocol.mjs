import crypto from "node:crypto";
import { readFileSync, statSync } from "node:fs";
import path from "node:path";

const EXTRACTOR = "text-lines@1";
const CHUNK_LINES = 80;
const REQUIRED_READ_KEYS = new Set(["path", "unit", "start", "end"]);
const COVERAGE_KEYS = new Set(["mode", "citations_required_for"]);
const GOVERNED_FINDING_FIELDS = Object.freeze([
  "positive_findings",
  "negative_findings",
]);

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("canonical values cannot contain undefined");
  return encoded;
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

export function canonicalHash(value) {
  return sha256(canonicalJson(value));
}

function defaultNormalizePath(value) {
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

function assertOnlyKeys(value, allowed, label) {
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) throw new Error(`unsupported ${label} field: ${key}`);
  }
}

function normalizeRequiredRead(raw, normalizePath, isAllowedPath) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("required_reads entries must be objects");
  }
  assertOnlyKeys(raw, REQUIRED_READ_KEYS, "required_reads");
  const relativePath = normalizePath(raw.path);
  if (!relativePath || !isAllowedPath(relativePath)) {
    throw new Error(`required read is outside allowed_paths: ${relativePath || raw.path}`);
  }
  if (raw.unit !== "line") throw new Error("required_reads unit must be line");
  const start = Number(raw.start);
  if (!Number.isInteger(start) || start < 1) {
    throw new Error("required_reads start must be a positive integer");
  }
  const end = raw.end === null ? null : Number(raw.end);
  if (end !== null && (!Number.isInteger(end) || end < start)) {
    throw new Error("required_reads end must be null or an integer at least start");
  }
  return Object.freeze({ path: relativePath, unit: "line", start, end });
}

function normalizeCoverageSpec(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("coverage_spec must be an object");
  }
  assertOnlyKeys(raw, COVERAGE_KEYS, "coverage_spec");
  if (raw.mode !== "ALL_REQUIRED_READS") {
    throw new Error("coverage_spec mode must be ALL_REQUIRED_READS");
  }
  if (!Array.isArray(raw.citations_required_for)) {
    throw new Error("coverage_spec citations_required_for must be an array");
  }
  const requested = new Set(raw.citations_required_for);
  if (
    requested.size !== raw.citations_required_for.length ||
    [...requested].some((field) => !GOVERNED_FINDING_FIELDS.includes(field))
  ) {
    throw new Error("coverage_spec citations_required_for contains an unsupported field");
  }
  if (GOVERNED_FINDING_FIELDS.some((field) => !requested.has(field))) {
    throw new Error(
      "coverage_spec citations_required_for must contain positive_findings and negative_findings",
    );
  }
  const citationsRequiredFor = GOVERNED_FINDING_FIELDS.filter((field) => requested.has(field));
  return Object.freeze({
    mode: "ALL_REQUIRED_READS",
    citationsRequiredFor: Object.freeze(citationsRequiredFor),
  });
}

export function normalizeEvidenceContract(
  raw = {},
  {
    normalizePath = defaultNormalizePath,
    isAllowedPath = () => true,
  } = {},
) {
  const suppliedReads = raw.required_reads ?? [];
  if (!Array.isArray(suppliedReads)) throw new Error("required_reads must be an array");
  if (suppliedReads.length === 0) {
    if (raw.coverage_spec !== undefined && raw.coverage_spec !== null) {
      throw new Error("coverage_spec requires non-empty required_reads");
    }
    return Object.freeze({
      requiredReads: Object.freeze([]),
      coverageSpec: null,
      coverageStatus: "NOT_REQUESTED",
      coverageHash: canonicalHash(null),
    });
  }
  if (raw.coverage_spec === undefined || raw.coverage_spec === null) {
    throw new Error("coverage_spec is required when required_reads are present");
  }
  const unique = new Map();
  for (const supplied of suppliedReads) {
    const read = normalizeRequiredRead(supplied, normalizePath, isAllowedPath);
    unique.set(canonicalJson(read), read);
  }
  const requiredReads = [...unique.values()].sort((left, right) =>
    left.path.localeCompare(right.path) ||
    left.start - right.start ||
    (left.end ?? Number.MAX_SAFE_INTEGER) - (right.end ?? Number.MAX_SAFE_INTEGER),
  );
  const coverageSpec = normalizeCoverageSpec(raw.coverage_spec);
  return Object.freeze({
    requiredReads: Object.freeze(requiredReads),
    coverageSpec,
    coverageStatus: "PENDING",
    coverageHash: canonicalHash(coverageSpec),
  });
}

function decodeUtf8(raw, relativePath) {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(raw);
  } catch {
    throw new Error(`required evidence is not valid UTF-8: ${relativePath}`);
  }
}

function manifestCore(manifest) {
  return {
    schema_version: manifest.schema_version,
    extractor: manifest.extractor,
    files: manifest.files,
  };
}

function buildFileManifest(relativePath, reads, resolvePath) {
  const fullPath = resolvePath(relativePath);
  let metadata;
  try {
    metadata = statSync(fullPath);
  } catch {
    throw new Error(`required evidence file does not exist: ${relativePath}`);
  }
  if (!metadata.isFile()) throw new Error(`required evidence is not a regular file: ${relativePath}`);
  const raw = readFileSync(fullPath);
  const text = decodeUtf8(raw, relativePath);
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  const requiredRanges = reads.map((read) => {
    const end = read.end ?? lines.length;
    if (read.start > lines.length || end > lines.length) {
      throw new Error(`required range exceeds line count for ${relativePath}`);
    }
    return Object.freeze({ start: read.start, end, unit: "line" });
  });
  const chunks = [];
  for (let offset = 0; offset < lines.length; offset += CHUNK_LINES) {
    const chunkLines = lines.slice(offset, offset + CHUNK_LINES);
    chunks.push(Object.freeze({
      start: offset + 1,
      end: offset + chunkLines.length,
      chunk_sha256: sha256(chunkLines.join("\n")),
    }));
  }
  return Object.freeze({
    relative_path: relativePath,
    byte_length: raw.length,
    encoding: "utf-8",
    line_count: lines.length,
    file_sha256: sha256(raw),
    required_ranges: Object.freeze(requiredRanges),
    chunks: Object.freeze(chunks),
  });
}

export function buildTextEvidenceManifest({ requiredReads, resolvePath }) {
  if (!Array.isArray(requiredReads) || requiredReads.length === 0) {
    throw new Error("requiredReads must be a non-empty array");
  }
  if (typeof resolvePath !== "function") throw new Error("resolvePath is required");
  const grouped = new Map();
  for (const read of requiredReads) {
    const existing = grouped.get(read.path) ?? [];
    existing.push(read);
    grouped.set(read.path, existing);
  }
  const files = [...grouped.keys()]
    .sort((left, right) => left.localeCompare(right))
    .map((relativePath) => buildFileManifest(relativePath, grouped.get(relativePath), resolvePath));
  const core = Object.freeze({
    schema_version: 1,
    extractor: EXTRACTOR,
    files: Object.freeze(files),
  });
  return Object.freeze({ ...core, manifest_hash: canonicalHash(core) });
}

export function assertManifestFresh(manifest, { resolvePath }) {
  if (!manifest || manifest.extractor !== EXTRACTOR || !Array.isArray(manifest.files)) {
    throw new Error("stale manifest: unsupported evidence manifest");
  }
  if (manifest.manifest_hash !== canonicalHash(manifestCore(manifest))) {
    throw new Error("stale manifest: manifest hash mismatch");
  }
  const requiredReads = manifest.files.flatMap((file) => file.required_ranges.map((range) => ({
    path: file.relative_path,
    unit: "line",
    start: range.start,
    end: range.end,
  })));
  let rebuilt;
  try {
    rebuilt = buildTextEvidenceManifest({ requiredReads, resolvePath });
  } catch (error) {
    throw new Error(`stale manifest: ${error.message}`);
  }
  if (rebuilt.manifest_hash !== manifest.manifest_hash) {
    throw new Error("stale manifest: source content changed");
  }
  return true;
}

function receiptCore({
  manifest,
  jobId,
  workspaceInstanceId,
  relativePath,
  start,
  end,
}) {
  if (!manifest || manifest.manifest_hash !== canonicalHash(manifestCore(manifest))) {
    throw new Error("cannot issue a receipt from an invalid manifest");
  }
  const file = manifest.files.find((entry) => entry.relative_path === relativePath);
  if (!file) throw new Error(`evidence path is not manifested: ${relativePath}`);
  if (
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 1 ||
    end < start ||
    end > file.line_count
  ) {
    throw new Error(`read range is outside manifested lines: ${relativePath}`);
  }
  const normalizedJobId = String(jobId ?? "").trim();
  const normalizedWorkspaceId = String(workspaceInstanceId ?? "").trim();
  if (!normalizedJobId || !normalizedWorkspaceId) {
    throw new Error("jobId and workspaceInstanceId are required for evidence receipts");
  }
  return Object.freeze({
    schema_version: 1,
    job_id: normalizedJobId,
    workspace_instance_id: normalizedWorkspaceId,
    manifest_hash: manifest.manifest_hash,
    relative_path: relativePath,
    file_sha256: file.file_sha256,
    chunk_sha256s: Object.freeze(
      file.chunks
        .filter((chunk) => chunk.end >= start && chunk.start <= end)
        .map((chunk) => chunk.chunk_sha256),
    ),
    start,
    end,
    unit: "line",
    next_start: end < file.line_count ? end + 1 : null,
    extractor: manifest.extractor,
  });
}

export function createReadReceipt(input) {
  const core = receiptCore(input);
  const receiptHash = canonicalHash(core);
  return Object.freeze({
    evidence_id: `EV-${receiptHash.slice(0, 32)}`,
    ...core,
    receipt_hash: receiptHash,
  });
}

function addError(errors, message) {
  const bounded = String(message ?? "evidence validation error")
    .replace(/[\r\n]+/g, " ")
    .slice(0, 240);
  if (!errors.includes(bounded) && errors.length < 20) errors.push(bounded);
}

function isCovered(intervals, requiredStart, requiredEnd) {
  const ordered = intervals
    .map(({ start, end }) => ({ start, end }))
    .sort((left, right) => left.start - right.start || left.end - right.end);
  let cursor = requiredStart;
  for (const interval of ordered) {
    if (interval.end < cursor) continue;
    if (interval.start > cursor) return false;
    cursor = Math.max(cursor, interval.end + 1);
    if (cursor > requiredEnd) return true;
  }
  return cursor > requiredEnd;
}

function nonemptyFinding(value) {
  if (typeof value === "string") return value.trim().length > 0;
  if (value === null || value === undefined) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

function validateReceipt(receipt, context) {
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt)) {
    throw new Error("tampered receipt: receipt must be an object");
  }
  const expected = createReadReceipt({
    manifest: context.manifest,
    jobId: context.jobId,
    workspaceInstanceId: context.workspaceInstanceId,
    relativePath: receipt.relative_path,
    start: receipt.start,
    end: receipt.end,
  });
  if (canonicalJson(receipt) !== canonicalJson(expected)) {
    throw new Error(`tampered receipt: ${receipt.evidence_id ?? "unknown"}`);
  }
  return expected;
}

function resolvedRequiredRange(read, manifest) {
  const file = manifest.files.find((entry) => entry.relative_path === read.path);
  if (!file) throw new Error(`required evidence is absent from manifest: ${read.path}`);
  return { path: read.path, start: read.start, end: read.end ?? file.line_count };
}

function validateCitations(handoff, coverageSpec, receiptsById, errors) {
  const supplied = handoff.citations ?? [];
  if (!Array.isArray(supplied)) {
    addError(errors, "citations must be an array");
    return [];
  }
  const governed = new Set(coverageSpec.citationsRequiredFor);
  const validated = [];
  const citedFindings = new Set();
  for (const citation of supplied) {
    if (!citation || typeof citation !== "object" || Array.isArray(citation)) {
      addError(errors, "citation must be an object");
      continue;
    }
    const field = citation.finding_field;
    const index = citation.finding_index;
    if (!governed.has(field)) {
      addError(errors, `citation has unsupported finding field: ${field}`);
      continue;
    }
    const findings = Array.isArray(handoff[field]) ? handoff[field] : [];
    if (!Number.isInteger(index) || index < 0 || index >= findings.length) {
      addError(errors, `citation finding index is invalid for ${field}`);
      continue;
    }
    if (!nonemptyFinding(findings[index])) {
      addError(errors, `citation finding index references an empty ${field} entry`);
      continue;
    }
    const receipt = receiptsById.get(citation.evidence_id);
    if (!receipt) {
      addError(errors, `citation references unknown evidence: ${citation.evidence_id}`);
      continue;
    }
    if (
      citation.unit !== "line" ||
      !Number.isInteger(citation.start) ||
      !Number.isInteger(citation.end) ||
      citation.start < receipt.start ||
      citation.end < citation.start ||
      citation.end > receipt.end
    ) {
      addError(errors, `citation range is outside receipt: ${citation.evidence_id}`);
      continue;
    }
    validated.push(Object.freeze({
      finding_field: field,
      finding_index: index,
      evidence_id: citation.evidence_id,
      start: citation.start,
      end: citation.end,
      unit: "line",
    }));
    citedFindings.add(`${field}:${index}`);
  }
  for (const field of governed) {
    const findings = Array.isArray(handoff[field]) ? handoff[field] : [];
    findings.forEach((finding, index) => {
      if (nonemptyFinding(finding) && !citedFindings.has(`${field}:${index}`)) {
        addError(errors, `required citation is missing for ${field}[${index}]`);
      }
    });
  }
  return validated;
}

export function validateEvidenceResult({
  handoff = {},
  manifest,
  receipts = [],
  requiredReads = [],
  coverageSpec,
  jobId,
  workspaceInstanceId,
  resolvePath,
}) {
  if (!Array.isArray(requiredReads) || requiredReads.length === 0) {
    return Object.freeze({
      coverage_status: "NOT_REQUESTED",
      execution_status: handoff.execution_status,
      evidence_verdict: handoff.evidence_verdict,
      files_inspected: Object.freeze([]),
      citations: Object.freeze([]),
      errors: Object.freeze([]),
    });
  }

  const errors = [];
  if (!coverageSpec || coverageSpec.mode !== "ALL_REQUIRED_READS") {
    addError(errors, "required coverage specification is invalid");
  }
  if (typeof resolvePath !== "function") {
    addError(errors, "required coverage cannot verify manifest freshness");
  } else {
    try {
      assertManifestFresh(manifest, { resolvePath });
    } catch (error) {
      addError(errors, error.message);
    }
  }

  const resolvedRanges = [];
  for (const read of requiredReads) {
    try {
      const resolved = resolvedRequiredRange(read, manifest);
      const file = manifest.files.find((entry) => entry.relative_path === resolved.path);
      const declared = file.required_ranges.some((range) =>
        range.start === resolved.start && range.end === resolved.end && range.unit === "line",
      );
      if (!declared) {
        addError(errors, `required range is not bound to manifest: ${resolved.path}`);
      }
      resolvedRanges.push(resolved);
    } catch (error) {
      addError(errors, error.message);
    }
  }

  const receiptsById = new Map();
  if (!Array.isArray(receipts)) {
    addError(errors, "runtime receipts must be an array");
  } else {
    for (const supplied of receipts) {
      try {
        const receipt = validateReceipt(supplied, { manifest, jobId, workspaceInstanceId });
        const prior = receiptsById.get(receipt.evidence_id);
        if (prior && canonicalJson(prior) !== canonicalJson(receipt)) {
          throw new Error(`tampered receipt: duplicate evidence id ${receipt.evidence_id}`);
        }
        receiptsById.set(receipt.evidence_id, receipt);
      } catch (error) {
        addError(errors, error.message.startsWith("tampered receipt")
          ? error.message
          : `tampered receipt: ${error.message}`);
      }
    }
  }

  for (const range of resolvedRanges) {
    const intervals = [...receiptsById.values()]
      .filter((receipt) => receipt.relative_path === range.path)
      .map((receipt) => ({ start: receipt.start, end: receipt.end }));
    if (!isCovered(intervals, range.start, range.end)) {
      addError(
        errors,
        `required coverage missing for ${range.path}:${range.start}-${range.end}`,
      );
    }
  }

  const citations = coverageSpec
    ? validateCitations(handoff, coverageSpec, receiptsById, errors)
    : [];
  const filesInspected = [...new Set(
    [...receiptsById.values()].map((receipt) => receipt.relative_path),
  )].sort((left, right) => left.localeCompare(right));
  const complete = errors.length === 0;
  return Object.freeze({
    coverage_status: complete ? "COMPLETE" : "INCOMPLETE",
    execution_status: complete ? handoff.execution_status : "INCOMPLETE",
    evidence_verdict: complete ? handoff.evidence_verdict : "UNRESOLVED",
    files_inspected: Object.freeze(filesInspected),
    citations: Object.freeze(citations),
    errors: Object.freeze(errors),
  });
}
