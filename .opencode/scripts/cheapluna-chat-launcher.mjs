import { execFileSync, spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const CHEAPLUNA_BUILD =
  "5756cbcfa419c2db7b9529639e905767af6ca5d80ff1e723bde1c688d19f7e25";
export const PROJECT_ID = "perfume-chem-cheapluna-isolated";

const SCRIPT_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(SCRIPT_DIRECTORY, "..", "..");
export const STATE_ROOT = path.join(PROJECT_ROOT, ".opencode", ".deepluna-home");
const STARTUP_CANARY_SCRIPT = path.join(
  os.homedir(),
  ".codex",
  "skills",
  "deepluna-chat",
  "scripts",
  "deepluna-chat.mjs",
);
export const SERVER_PATH = path.join(
  String(
    process.env.LOCALAPPDATA ??
      path.join(os.homedir(), "AppData", "Local"),
  ),
  "OpenCode",
  "CheapLuna",
  "runtime",
  CHEAPLUNA_BUILD,
  "server.mjs",
);

function hiddenPowerShell(script) {
  return execFileSync(
    "powershell.exe",
    ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
    {
      encoding: "utf8",
      windowsHide: true,
      stdio: ["ignore", "pipe", "ignore"],
    },
  ).trim();
}

function readUserEnvironmentVariable(name) {
  if (process.platform !== "win32") return "";
  try {
    return hiddenPowerShell(
      `[Console]::Out.Write([Environment]::GetEnvironmentVariable('${name}', 'User'))`,
    );
  } catch {
    return "";
  }
}

export function buildChatEnvironment(
  source = process.env,
  readUserValue = readUserEnvironmentVariable,
) {
  const environment = { ...source };
  const providerToken =
    String(environment.PERFUME_DEEPSEEK_API_KEY ?? "").trim() ||
    String(readUserValue("PERFUME_DEEPSEEK_API_KEY") ?? "").trim() ||
    String(readUserValue("DEEPSEEK_API_KEY") ?? "").trim();
  if (!providerToken) {
    throw new Error("direct DeepSeek credential is unavailable");
  }

  Object.assign(environment, {
    DEEPLUNA_PRIMARY_PROFILE: "cheapluna-chat",
    DEEPLUNA_FAST_ONLY: "0",
    DEEPLUNA_CODEX_ORCHESTRATION: "disabled",
    DEEPLUNA_READER_POOL_MODE: "DYNAMIC",
    DEEPLUNA_EMBEDDED_COMPAT: "",
    DEEPLUNA_PROJECT_SCOPE: "project",
    DEEPLUNA_PROJECT_ID: PROJECT_ID,
    DEEPSEEK_ALLOWED_ROOT: PROJECT_ROOT,
    NANODRUG_PROJECT_ROOT: PROJECT_ROOT,
    DEEPSEEK_ORCHESTRATOR_HOME: STATE_ROOT,
    NANODRUG_DEEPINFRA_READER_LANES: "50",
    NANODRUG_DEEPINFRA_WRITER_LANES: "10",
    DEEPSEEK_API_KEY: providerToken,
  });
  delete environment.DEEPINFRA_API_TOKEN;
  delete environment.DEEPSEEK_BASE_URL;
  delete environment.DEEPLUNA_CODEX_EXECUTABLE;
  delete environment.DEEPLUNA_PRESERVE_PROJECT_BINDINGS;
  delete environment.DEEPLUNA_READER_POOL_OWNER_PROJECT_ID;
  return environment;
}

function applyProcessEnvironment(environment) {
  for (const key of Object.keys(process.env)) {
    if (
      key === "DEEPINFRA_API_TOKEN" ||
      key === "DEEPSEEK_BASE_URL" ||
      key === "DEEPLUNA_CODEX_EXECUTABLE" ||
      key === "DEEPLUNA_PRESERVE_PROJECT_BINDINGS" ||
      key === "DEEPLUNA_READER_POOL_OWNER_PROJECT_ID"
    ) {
      delete process.env[key];
    }
  }
  for (const [key, value] of Object.entries(environment)) {
    if (value !== undefined) process.env[key] = String(value);
  }
}

function assertLocalInputs() {
  const relativeState = path.relative(PROJECT_ROOT, STATE_ROOT);
  if (
    relativeState === "" ||
    relativeState.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relativeState)
  ) {
    throw new Error("mutable state escaped the Perfume-Chem project root");
  }
  if (!fs.existsSync(SERVER_PATH) || !fs.statSync(SERVER_PATH).isFile()) {
    throw new Error("pinned immutable Chat runtime is missing");
  }
}

function windowsDaemonOwners() {
  if (process.platform !== "win32") return [];
  const marker = `--project-id=${PROJECT_ID}`;
  const script =
    `$marker='${marker}'; ` +
    "$owners=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | " +
    "Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -like '*--daemon*' " +
    "-and $_.CommandLine -like ('*' + $marker + '*') } | " +
    "Select-Object ProcessId,CommandLine); " +
    "if($owners.Count -gt 0){$owners | ConvertTo-Json -Compress}";
  let raw;
  try {
    raw = hiddenPowerShell(script);
  } catch {
    throw new Error("could not verify the exact-project daemon owner");
  }
  if (!raw) return [];
  const parsed = JSON.parse(raw);
  return Array.isArray(parsed) ? parsed : [parsed];
}

function assertExactDaemonOwners() {
  const owners = windowsDaemonOwners();
  if (owners.length > 1) {
    throw new Error("multiple exact-project daemon owners were found");
  }
  if (
    owners.length === 1 &&
    !String(owners[0].CommandLine ?? "")
      .toLowerCase()
      .includes(SERVER_PATH.toLowerCase())
  ) {
    throw new Error("a foreign exact-project daemon owner holds the pipe");
  }
  return owners;
}

function validateHealth(health) {
  if (
    health?.project_id !== PROJECT_ID ||
    health?.capacity?.read_limit !== 50 ||
    health?.capacity?.write_limit !== 10 ||
    !["READY", "DEGRADED", "BLOCKED"].includes(health?.readiness)
  ) {
    throw new Error("daemon failed exact-project identity validation");
  }
  return health;
}

async function attemptHealth(connect) {
  let client;
  try {
    client = await connect();
  } catch (error) {
    return { kind: "UNAVAILABLE", error };
  }
  try {
    return {
      kind: "VALID",
      health: validateHealth(await client.request("health", {})),
    };
  } catch (error) {
    return { kind: "INVALID", error };
  } finally {
    await client.close();
  }
}

function startDetachedDaemon(environment) {
  const child = spawn(
    process.execPath,
    [SERVER_PATH, "--daemon", `--project-id=${PROJECT_ID}`],
    {
      cwd: PROJECT_ROOT,
      env: environment,
      detached: true,
      windowsHide: true,
      stdio: "ignore",
    },
  );
  child.on("error", () => {});
  child.unref();
}

export async function ensureExactProjectDaemon({
  connect,
  environment,
  ownerCount,
  sleep = (delayMs) => new Promise((resolve) => setTimeout(resolve, delayMs)),
  now = Date.now,
  timeoutMs = 15_000,
} = {}) {
  if (typeof connect !== "function") {
    throw new TypeError("daemon connector is required");
  }
  const first = await attemptHealth(connect);
  if (first.kind === "VALID") return { reused: true, health: first.health };
  if (first.kind === "INVALID") throw first.error;

  if (ownerCount === 0) startDetachedDaemon(environment);
  const deadline = now() + timeoutMs;
  while (now() < deadline) {
    await sleep(250);
    const result = await attemptHealth(connect);
    if (result.kind === "VALID") {
      return { reused: ownerCount === 1, health: result.health };
    }
    if (result.kind === "INVALID") throw result.error;
  }
  throw new Error("exact-project daemon did not become available");
}

export function runStartupCanaryOnce({
  environment,
  health,
  stateRoot = STATE_ROOT,
  canaryScript = STARTUP_CANARY_SCRIPT,
  spawnCanary = spawnSync,
  now = Date.now,
} = {}) {
  if (!health || typeof health !== "object") {
    throw new TypeError("startup canary requires exact-project health");
  }
  const processBootId = String(health.process_boot_id ?? "").trim();
  if (!/^DI-[a-f0-9]{32}$/.test(processBootId)) {
    throw new Error("startup canary requires a valid process boot identity");
  }
  const admissible =
    health.project_id === PROJECT_ID &&
    health.readiness === "READY" &&
    health.circuits?.provider_calls_enabled === true &&
    health.budget?.unknown_reservations === 0 &&
    health.budget?.open_reserved_nano_usd === 0 &&
    health.capacity?.active_reads === 0 &&
    health.capacity?.active_writes === 0 &&
    health.capacity?.queued === 0;
  if (!admissible) {
    return Object.freeze({
      schema_version: 1,
      process_boot_id: processBootId,
      project_id: health.project_id ?? null,
      status: "BLOCKED",
      reused: false,
      provider_transmission_attempted: false,
      reason: "DEEPLUNA_CHAT_NOT_ADMISSIBLE",
    });
  }

  const receiptDirectory = path.join(stateRoot, "startup-canary");
  const receiptPath = path.join(receiptDirectory, `${processBootId}.json`);
  const lockPath = `${receiptPath}.lock`;
  fs.mkdirSync(receiptDirectory, { recursive: true });
  if (fs.existsSync(receiptPath)) {
    return Object.freeze({
      ...JSON.parse(fs.readFileSync(receiptPath, "utf8")),
      reused: true,
    });
  }

  let lockDescriptor;
  try {
    lockDescriptor = fs.openSync(lockPath, "wx", 0o600);
  } catch (error) {
    if (error?.code === "EEXIST") {
      return Object.freeze({
        schema_version: 1,
        process_boot_id: processBootId,
        project_id: PROJECT_ID,
        status: "IN_PROGRESS",
        reused: true,
        provider_transmission_attempted: false,
      });
    }
    throw error;
  }

  try {
    fs.closeSync(lockDescriptor);
    lockDescriptor = undefined;
    const result = spawnCanary(process.execPath, [canaryScript, "canary"], {
      cwd: PROJECT_ROOT,
      env: environment,
      encoding: "utf8",
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
      maxBuffer: 1024 * 1024,
    });
    const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
    const passed =
      result.status === 0 &&
      /"status"\s*:\s*"PASS"/.test(output) &&
      output.includes("DEEPLUNA_CHAT_CANARY_OK");
    const receipt = Object.freeze({
      schema_version: 1,
      process_boot_id: processBootId,
      project_id: PROJECT_ID,
      status: passed ? "PASS" : "FAIL",
      reused: false,
      provider_transmission_attempted: true,
      exit_code: result.status ?? null,
      public_job_id: output.match(/"job_id"\s*:\s*"(DS-[a-f0-9]{32})"/)?.[1] ?? null,
      output_sha256: createHash("sha256").update(output, "utf8").digest("hex"),
      completed_at_ms: now(),
    });
    const temporaryPath = `${receiptPath}.${process.pid}.tmp`;
    fs.writeFileSync(temporaryPath, `${JSON.stringify(receipt, null, 2)}\n`, {
      encoding: "utf8",
      flag: "wx",
      mode: 0o600,
    });
    fs.renameSync(temporaryPath, receiptPath);
    return receipt;
  } finally {
    if (lockDescriptor !== undefined) fs.closeSync(lockDescriptor);
    fs.rmSync(lockPath, { force: true });
  }
}

export async function launchChat() {
  assertLocalInputs();
  const environment = buildChatEnvironment();
  applyProcessEnvironment(environment);
  const owners = assertExactDaemonOwners();
  const { connectProductionCandidateDaemon, main } = await import(
    pathToFileURL(SERVER_PATH).href
  );
  const daemon = await ensureExactProjectDaemon({
    connect: () => connectProductionCandidateDaemon(),
    environment,
    ownerCount: owners.length,
  });
  const canary = runStartupCanaryOnce({ environment, health: daemon.health });
  if (!canary.reused) {
    process.stderr.write(
      `DeepLuna Chat startup canary ${canary.status} for ${canary.process_boot_id}\n`,
    );
  }
  await main();
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  launchChat().catch((error) => {
    const message = String(error?.message ?? error)
      .replaceAll(/[\r\n]+/g, " ")
      .slice(0, 1_000);
    console.error(`DeepLuna Chat launcher failed: ${message}`);
    process.exit(1);
  });
}
