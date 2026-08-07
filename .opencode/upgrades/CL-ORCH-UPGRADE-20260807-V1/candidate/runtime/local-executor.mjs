import crypto from "node:crypto";
import {
  closeSync,
  existsSync,
  fstatSync,
  fsyncSync,
  lstatSync,
  mkdirSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmdirSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";

const EMPTY_USAGE = Object.freeze({
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
  prompt_cache_hit_tokens: 0,
  prompt_cache_miss_tokens: 0,
});

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function pathIsWithin(root, target) {
  const relative = path.relative(root, target);
  return relative === "" ||
    (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function portablePath(value) {
  return value.replaceAll("\\", "/").replace(/^\.\//, "");
}

function sameFileIdentity(left, right) {
  return (
    left.dev === right.dev &&
    left.ino === right.ino &&
    left.size === right.size &&
    left.mode === right.mode &&
    left.nlink === right.nlink &&
    left.mtimeNs === right.mtimeNs &&
    left.ctimeNs === right.ctimeNs
  );
}

function assertNoReparsePoint(workspace, target) {
  const relative = path.relative(workspace, target);
  if (!relative) {
    if (lstatSync(workspace).isSymbolicLink()) {
      throw new Error("LOCAL exact-byte workspace contains a reparse point");
    }
    return;
  }
  let current = workspace;
  for (const part of relative.split(path.sep)) {
    current = path.join(current, part);
    if (existsSync(current) && lstatSync(current).isSymbolicLink()) {
      throw new Error("LOCAL exact-byte target contains a reparse point");
    }
  }
}

function canonicalBase64(value) {
  if (typeof value !== "string") {
    throw new Error("LOCAL exact-byte payload must be canonical base64");
  }
  const bytes = Buffer.from(value, "base64");
  if (bytes.toString("base64") !== value) {
    throw new Error("LOCAL exact-byte payload must be canonical base64");
  }
  return bytes;
}

function removeOwnedFile(filePath) {
  try {
    if (existsSync(filePath)) unlinkSync(filePath);
  } catch {
    // The primary transaction error remains authoritative.
  }
}

function removeOwnedEmptyDirectory(directory) {
  try {
    if (existsSync(directory)) rmdirSync(directory);
  } catch {
    // A non-empty or concurrently replaced directory is never removed.
  }
}

function writeFlushedExclusive(filePath, bytes, mode) {
  let descriptor;
  try {
    descriptor = openSync(filePath, "wx", mode);
    writeFileSync(descriptor, bytes);
    fsyncSync(descriptor);
    const stat = fstatSync(descriptor, { bigint: true });
    if (!stat.isFile() || stat.size !== BigInt(bytes.length)) {
      throw new Error("LOCAL exact-byte staged file size mismatch");
    }
  } finally {
    if (descriptor !== undefined) closeSync(descriptor);
  }
}

function exactWriteTarget(task, verification) {
  const workspace = realpathSync.native(path.resolve(String(task.workspace ?? "")));
  const relative = portablePath(String(verification.path ?? ""));
  if (!relative || path.isAbsolute(relative)) {
    throw new Error("LOCAL exact-byte target must be workspace-relative");
  }
  const target = path.resolve(workspace, relative);
  if (!pathIsWithin(workspace, target)) {
    throw new Error("LOCAL exact-byte target is outside the workspace");
  }
  const allowed = Array.isArray(task.allowedPaths) &&
    task.allowedPaths.some((entry) => {
      const allowedTarget = path.resolve(workspace, String(entry ?? ""));
      return pathIsWithin(workspace, allowedTarget) &&
        pathIsWithin(allowedTarget, target);
    });
  if (!allowed) {
    throw new Error("LOCAL exact-byte target is outside allowed_paths");
  }
  assertNoReparsePoint(workspace, target);
  if (!existsSync(target)) {
    throw new Error("LOCAL exact-byte target must already exist");
  }
  const targetStat = lstatSync(target, { bigint: true });
  if (targetStat.isSymbolicLink() || !targetStat.isFile()) {
    throw new Error("LOCAL exact-byte target must be a regular file");
  }
  if (targetStat.nlink !== 1n) {
    throw new Error("LOCAL exact-byte target must not be hard linked");
  }
  const canonicalTarget = realpathSync.native(target);
  if (!pathIsWithin(workspace, canonicalTarget)) {
    throw new Error("LOCAL exact-byte target resolves outside the workspace");
  }
  return Object.freeze({
    workspace,
    relative,
    target,
    targetStat,
    mode: Number(targetStat.mode & 0o777n),
  });
}

/**
 * Materialize one host-authoritative exact-byte WRITE contract locally.
 *
 * The payload is canonical base64 and is verified before any archive or target
 * mutation. A flushed same-directory staging file is atomically renamed over
 * the existing target only after its identity is rechecked.
 */
export async function runLocalExactWriteContract(task, options = {}) {
  if (task?.mode !== "WRITE") {
    throw new Error("LOCAL exact-byte route requires WRITE mode");
  }
  const verifications = Array.isArray(task.writeVerifications)
    ? [...task.writeVerifications]
    : [];
  if (verifications.length !== 1) {
    throw new Error("LOCAL exact-byte route requires exactly one write_verifications entry");
  }
  const verification = verifications[0];
  const bytes = canonicalBase64(verification.content_base64);
  const expectedLength = Number(verification.byte_length);
  const expectedSha256 = String(verification.sha256 ?? "");
  if (
    !Number.isSafeInteger(expectedLength) ||
    expectedLength < 0 ||
    bytes.length !== expectedLength ||
    !/^[a-f0-9]{64}$/.test(expectedSha256) ||
    sha256(bytes) !== expectedSha256
  ) {
    throw new Error("LOCAL exact-byte payload does not match declared hash and length");
  }

  const resolved = exactWriteTarget(task, verification);
  const original = readFileSync(resolved.target);
  const afterRead = lstatSync(resolved.target, { bigint: true });
  if (!sameFileIdentity(resolved.targetStat, afterRead)) {
    throw new Error("LOCAL exact-byte target changed during capture");
  }
  const directory = path.dirname(resolved.target);
  const transactionId = crypto.randomUUID();
  const stagedPath = path.join(
    directory,
    `.${path.basename(resolved.target)}.deepluna-${transactionId}.tmp`,
  );
  const restorePath = path.join(
    directory,
    `.${path.basename(resolved.target)}.deepluna-${transactionId}.restore`,
  );
  const archiveRoot = path.join(resolved.workspace, ".archive");
  const archiveRootExisted = existsSync(archiveRoot);
  let archivePath = null;
  let commitAttempted = false;
  let renamed = false;
  const renameFile = options.renameFile ?? renameSync;

  try {
    writeFlushedExclusive(stagedPath, bytes, resolved.mode);
    const staged = readFileSync(stagedPath);
    if (staged.length !== expectedLength || sha256(staged) !== expectedSha256) {
      throw new Error("LOCAL exact-byte staged payload verification failed");
    }
    const beforeCommit = lstatSync(resolved.target, { bigint: true });
    if (!sameFileIdentity(resolved.targetStat, beforeCommit)) {
      throw new Error("LOCAL exact-byte target changed before commit");
    }

    if (archiveRootExisted) {
      const archiveStat = lstatSync(archiveRoot);
      if (archiveStat.isSymbolicLink() || !archiveStat.isDirectory()) {
        throw new Error("LOCAL exact-byte archive root is unsafe");
      }
    } else {
      mkdirSync(archiveRoot, { mode: 0o700 });
    }
    const canonicalArchiveRoot = realpathSync.native(archiveRoot);
    if (!pathIsWithin(resolved.workspace, canonicalArchiveRoot)) {
      throw new Error("LOCAL exact-byte archive root resolves outside the workspace");
    }
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
    archivePath = path.join(
      canonicalArchiveRoot,
      `${path.basename(resolved.relative)}.${stamp}_${transactionId.slice(0, 8)}.bak`,
    );
    writeFlushedExclusive(archivePath, original, resolved.mode);
    if (!readFileSync(archivePath).equals(original)) {
      throw new Error("LOCAL exact-byte archive verification failed");
    }

    commitAttempted = true;
    renameFile(stagedPath, resolved.target);
    renamed = true;
    const actual = readFileSync(resolved.target);
    if (actual.length !== expectedLength || sha256(actual) !== expectedSha256) {
      throw new Error("LOCAL exact-byte committed payload verification failed");
    }

    const archiveRelative = portablePath(path.relative(resolved.workspace, archivePath));
    const receipt = Object.freeze({
      kind: "LOCAL_EXACT_BYTES",
      phase: "HOST_LOCAL_COMMIT",
      path: resolved.relative,
      expected_sha256: expectedSha256,
      expected_byte_length: expectedLength,
      actual_sha256: sha256(actual),
      actual_byte_length: actual.length,
      archive_path: archiveRelative,
      passed: true,
      error_code: null,
    });
    return Object.freeze({
      status: "PASS",
      execution_status: "ACCEPTED",
      evidence_verdict: "NOT_APPLICABLE",
      summary: `Committed exact bytes locally for ${resolved.relative}.`,
      files_inspected: Object.freeze([]),
      files_changed: Object.freeze([resolved.relative, archiveRelative]),
      commands_run: Object.freeze([]),
      tests: Object.freeze([
        `LOCAL_EXACT_BYTES PASS path=${resolved.relative} sha256=${expectedSha256} ` +
          `byte_length=${expectedLength}`,
      ]),
      positive_findings: Object.freeze([]),
      negative_findings: Object.freeze([]),
      scientific_uncertainty: false,
      architecture_uncertainty: false,
      scope_deviation: false,
      residual_risks: Object.freeze([]),
      recommended_next_action: "Return the host-verification receipt to Sol.",
      write_verification_receipts: Object.freeze([receipt]),
      api_calls: 0,
      usage: EMPTY_USAGE,
      receipts: Object.freeze([receipt]),
      assertion_receipts: Object.freeze([]),
    });
  } catch (error) {
    let rollbackError = null;
    if (commitAttempted) {
      try {
        assertNoReparsePoint(resolved.workspace, resolved.target);
        let targetMatchesOriginal = false;
        if (existsSync(resolved.target)) {
          const currentStat = lstatSync(resolved.target, { bigint: true });
          if (
            currentStat.isSymbolicLink() ||
            !currentStat.isFile() ||
            currentStat.nlink !== 1n
          ) {
            throw new Error("LOCAL exact-byte rollback target is unsafe");
          }
          const canonicalTarget = realpathSync.native(resolved.target);
          if (!pathIsWithin(resolved.workspace, canonicalTarget)) {
            throw new Error("LOCAL exact-byte rollback target escaped the workspace");
          }
          targetMatchesOriginal = readFileSync(resolved.target).equals(original);
        }
        if (!targetMatchesOriginal) {
          removeOwnedFile(restorePath);
          writeFlushedExclusive(restorePath, original, resolved.mode);
          renameSync(restorePath, resolved.target);
          if (!readFileSync(resolved.target).equals(original)) {
            throw new Error("LOCAL exact-byte rollback verification failed");
          }
        }
        renamed = false;
      } catch (failure) {
        rollbackError = failure;
      }
    }
    if (rollbackError) {
      const combined = new Error(
        `LOCAL exact-byte rollback failed after commit attempt: ${rollbackError.message}; ` +
        `original error: ${error?.message ?? String(error)}`,
        { cause: rollbackError },
      );
      combined.code = "LOCAL_EXACT_WRITE_ROLLBACK_FAILED";
      throw combined;
    }
    if (!renamed) {
      removeOwnedFile(stagedPath);
      removeOwnedFile(restorePath);
      if (archivePath) removeOwnedFile(archivePath);
      if (!archiveRootExisted) removeOwnedEmptyDirectory(archiveRoot);
    }
    throw error;
  }
}

/**
 * Execute one frozen deterministic READ_ONLY command contract.
 *
 * The caller owns command validation and injects a supervised runner. This module
 * never invokes a shell, provider, model, or repository tool by itself.
 */
export async function runLocalReadContract(task, options = {}) {
  if (task?.mode !== "READ_ONLY") {
    throw new Error("LOCAL route requires READ_ONLY mode");
  }

  const commands = Array.isArray(task.commandsTests)
    ? [...task.commandsTests]
    : [];
  if (commands.length === 0) {
    throw new Error("LOCAL route requires commands_tests");
  }
  if (commands.length > 8) {
    throw new Error("LOCAL route permits at most 8 commands");
  }
  if (commands.some((command) => typeof command !== "string" || command.length > 1_000)) {
    throw new Error("LOCAL command exceeds 1000 characters");
  }

  const commandRunner = options.commandRunner;
  if (typeof commandRunner !== "function") {
    throw new Error("LOCAL command runner is unavailable");
  }

  const maximumOutputBytes = options.maximumOutputBytes ?? (64 * 1024);
  const maximumReceiptStreamBytes = options.maximumReceiptStreamBytes ?? (4 * 1024);
  const signal = options.signal;
  const nowFunction = options.nowFunction ?? Date.now;
  const deadlineMs = Number.isFinite(options.deadlineMs)
    ? options.deadlineMs
    : nowFunction() + task.timeoutMs;
  const hashText = options.hashText ??
    ((value) => crypto.createHash("sha256").update(String(value)).digest("hex"));
  const abortError = (message) => {
    const error = new Error(message);
    error.name = "AbortError";
    return error;
  };
  const remainingTime = () => {
    if (signal?.aborted) throw abortError("LOCAL command execution aborted");
    const remaining = Math.floor(deadlineMs - nowFunction());
    if (remaining <= 0) throw abortError("LOCAL command deadline exceeded");
    return remaining;
  };
  const boundedUtf8 = (value, maximumBytes) => {
    let result = "";
    let bytes = 0;
    for (const character of value) {
      const characterBytes = Buffer.byteLength(character);
      if (bytes + characterBytes > maximumBytes) break;
      result += character;
      bytes += characterBytes;
    }
    return result;
  };
  const receipts = [];
  const fullOutputs = [];
  let cumulativeOutputBytes = 0;
  let contractError = false;
  for (const [index, command] of commands.entries()) {
    const timeoutMs = Math.min(task.timeoutMs, remainingTime());
    const commandSpec = task.localCommandSpecs?.[index] ?? null;
    const commandSnapshot = options.commandSnapshots?.[index] ?? null;
    if (commandSpec && !commandSnapshot) {
      throw new Error("LOCAL command snapshot is unavailable");
    }
    if (commandSnapshot) options.verifySnapshot?.(commandSnapshot);
    const completed = await commandRunner(command, {
      cwd: task.workspace,
      timeoutMs,
      signal,
      commandSpec,
      snapshotPath: commandSnapshot?.snapshotPath,
      snapshotContent: commandSnapshot?.snapshotContent,
      capturedSha256: commandSnapshot?.capturedSha256,
      nodeModuleType: commandSnapshot?.nodeModuleType,
    });
    remainingTime();
    if (commandSnapshot) options.verifySnapshot?.(commandSnapshot);
    const stdout = String(completed.stdout ?? "");
    const stderr = String(completed.stderr ?? "");
    const stdoutBytes = Buffer.byteLength(stdout);
    const stderrBytes = Buffer.byteLength(stderr);
    cumulativeOutputBytes += stdoutBytes + stderrBytes;
    if (cumulativeOutputBytes > maximumOutputBytes) {
      throw new Error("LOCAL_OUTPUT_LIMIT");
    }
    const exitCode =
      completed.exit_code ?? completed.exitCode ?? completed.code;
    const validExitCode = Number.isInteger(exitCode) && Number.isFinite(exitCode);
    fullOutputs.push(Object.freeze({ stdout, stderr }));
    receipts.push(Object.freeze({
      command,
      exit_code: validExitCode ? exitCode : null,
      stdout: boundedUtf8(stdout, maximumReceiptStreamBytes),
      stderr: boundedUtf8(stderr, maximumReceiptStreamBytes),
      stdout_bytes: stdoutBytes,
      stderr_bytes: stderrBytes,
      stdout_sha256: hashText(stdout),
      stderr_sha256: hashText(stderr),
      output_sha256: hashText(`${stdout}\0${stderr}`),
    }));
    if (!validExitCode) {
      contractError = true;
      break;
    }
  }

  const allExitZero =
    receipts.length === commands.length &&
    receipts.every((receipt) => receipt.exit_code === 0);
  const assertions = Array.isArray(task.localAssertions)
    ? task.localAssertions
    : [];
  const assertionReceipts = assertions.map((assertion) => {
    const streamText = fullOutputs[assertion.command_index]?.[assertion.stream] ?? "";
    const matched = streamText.includes(assertion.pattern);
    const passed = assertion.must_match ? matched : !matched;
    return Object.freeze({
      command_index: assertion.command_index,
      stream: assertion.stream,
      pattern_sha256: hashText(assertion.pattern),
      pattern_chars: assertion.pattern.length,
      must_match: assertion.must_match,
      matched,
      passed,
    });
  });
  const assertionsPass = assertionReceipts.every((receipt) => receipt.passed);
  const accepted = !contractError && allExitZero && assertionsPass;
  const frozenReceipts = Object.freeze(receipts);
  const frozenAssertionReceipts = Object.freeze(assertionReceipts);
  return Object.freeze({
    status: accepted ? "PASS" : "FAIL",
    execution_status: accepted
      ? "ACCEPTED"
      : contractError
        ? "CONTRACT_ERROR"
        : "INCOMPLETE",
    evidence_verdict: accepted ? "NOT_APPLICABLE" : "UNRESOLVED",
    api_calls: 0,
    usage: EMPTY_USAGE,
    receipts: frozenReceipts,
    assertion_receipts: frozenAssertionReceipts,
  });
}
