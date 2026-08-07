#!/usr/bin/env node

/*
 * Deterministic, currently unwired Task 6 command supervision helpers.
 *
 * Process behavior follows Microsoft taskkill and Node child_process documentation:
 * exact PID selection, descendant termination, no shell, one spawn, bounded UTF-8 capture,
 * and one settlement across error/close/termination races. Pytest shards use fixed xdist
 * worker counts, load distribution, and disabled worker restarts.
 */

import { spawn, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import { EventEmitter } from "node:events";
import net from "node:net";
import path from "node:path";

import {
  capacityLaneForRole,
  resolveCapacityPolicy,
  WeightedFairScheduler,
} from "./lib/capacity-policy.mjs";
import {
  DEFAULT_PROVIDER_POOL_POLICY,
  ProviderPoolRegistry,
} from "./lib/provider-pools.mjs";
import {
  openSchedulerStore,
  readCandidateActivationQuiescenceSnapshot,
} from "./lib/scheduler-store.mjs";
import {
  CANDIDATE_DAEMON_PROFILE,
  CANDIDATE_DAEMON_RELEASE,
  CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
  CANDIDATE_DAEMON_RUNTIME_ACCEPTED,
  CANDIDATE_DAEMON_WIRE_LIMITS,
  CANDIDATE_PROCESS_BOOT_ID,
  CANDIDATE_PROCESS_STARTED_AT_MS,
  CANDIDATE_RUNTIME_BUILD_HASH,
  candidateDaemonPipeNameForProject,
  candidateHandshakeTranscriptHash,
  canonicalCandidateDaemonJson,
  createCandidateClientFinish,
  createCandidateClientHello,
  createCandidateServerFinish,
  createCandidateServerHello,
  validateCandidateRpcRequestEnvelope,
  validateCandidateRpcResponseEnvelope,
  verifyCandidateClientFinish,
  verifyCandidateClientHello,
  verifyCandidateServerFinish,
  verifyCandidateServerHello,
} from "./lib/daemon-protocol-v2.mjs";

const MAX_CAPTURE_BYTES = 64 * 1024;
const MAX_TIMER_DELAY_MS = 2_147_483_647;
const MAX_WINDOWS_PID = 0xffffffff;
const MAX_PYTEST_WORKERS = 32;
const INVALID_PROCESS_ID = "refusing to terminate an invalid process id";
const INVALID_PROCESS_TREE_OPTIONS = "invalid process tree options";
const PROCESS_TREE_FAILURE = "process tree termination failed";
const INVALID_SUPERVISED_OPTIONS = "invalid supervised command options";
const INVALID_CHILD_PID = "invalid supervised child process id";
const INVALID_SHARD_INPUT = "invalid pytest shard input";
const CANDIDATE_PIPE_ACL_FAILURE =
  "candidate named-pipe ACL attestation failed";
const CANDIDATE_PIPE_OWNER_FAILURE =
  "candidate named-pipe server PID attestation failed";
const AUTHENTICATED_CANDIDATE_ORIGIN_SESSIONS = new WeakSet();

const CANDIDATE_PIPE_ACL_POWERSHELL = String.raw`
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Add-Type -Language CSharp -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using Microsoft.Win32.SafeHandles;

public static class DeepLunaCandidatePipeAcl
{
    private const uint READ_CONTROL = 0x00020000;
    private const uint WRITE_DAC = 0x00040000;
    private const uint OPEN_EXISTING = 3;
    private const uint SECURITY_SQOS_PRESENT = 0x00100000;
    private const uint SECURITY_ANONYMOUS = 0x00000000;
    private const uint DACL_SECURITY_INFORMATION = 0x00000004;
    private const uint PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000;
    private const uint GENERIC_ALL = 0x10000000;
    private const uint FILE_ALL_ACCESS = 0x001F01FF;
    private const int SE_KERNEL_OBJECT = 6;
    private const uint SDDL_REVISION_1 = 1;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(
        string name,
        uint desiredAccess,
        uint shareMode,
        IntPtr securityAttributes,
        uint creationDisposition,
        uint flagsAndAttributes,
        IntPtr templateFile);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(
        string stringSecurityDescriptor,
        uint stringSDRevision,
        out IntPtr securityDescriptor,
        out uint securityDescriptorSize);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetSecurityDescriptorDacl(
        IntPtr securityDescriptor,
        out bool daclPresent,
        out IntPtr dacl,
        out bool daclDefaulted);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint SetSecurityInfo(
        SafeFileHandle handle,
        int objectType,
        uint securityInfo,
        IntPtr owner,
        IntPtr group,
        IntPtr dacl,
        IntPtr sacl);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint GetSecurityInfo(
        SafeFileHandle handle,
        int objectType,
        uint securityInfo,
        out IntPtr owner,
        out IntPtr group,
        out IntPtr dacl,
        out IntPtr sacl,
        out IntPtr securityDescriptor);

    [DllImport("advapi32.dll")]
    private static extern uint GetSecurityDescriptorLength(IntPtr securityDescriptor);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr memory);

    private static Exception Win32(string operation)
    {
        return new Win32Exception(Marshal.GetLastWin32Error(), operation);
    }

    public static string ProtectAndAttest(string pipePath)
    {
        SecurityIdentifier currentSid = WindowsIdentity.GetCurrent().User;
        if (currentSid == null)
        {
            throw new InvalidOperationException("current Windows identity has no SID");
        }

        using (SafeFileHandle handle = CreateFileW(
            pipePath,
            READ_CONTROL | WRITE_DAC,
            0,
            IntPtr.Zero,
            OPEN_EXISTING,
            SECURITY_SQOS_PRESENT | SECURITY_ANONYMOUS,
            IntPtr.Zero))
        {
            if (handle.IsInvalid)
            {
                throw Win32("open named pipe for ACL");
            }

            IntPtr desiredDescriptor = IntPtr.Zero;
            IntPtr actualDescriptor = IntPtr.Zero;
            try
            {
                string sddl = "D:P(A;;GA;;;" + currentSid.Value + ")";
                uint ignoredSize;
                if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    sddl,
                    SDDL_REVISION_1,
                    out desiredDescriptor,
                    out ignoredSize))
                {
                    throw Win32("construct named-pipe DACL");
                }

                bool daclPresent;
                bool daclDefaulted;
                IntPtr desiredDacl;
                if (!GetSecurityDescriptorDacl(
                    desiredDescriptor,
                    out daclPresent,
                    out desiredDacl,
                    out daclDefaulted) ||
                    !daclPresent ||
                    desiredDacl == IntPtr.Zero)
                {
                    throw Win32("read constructed named-pipe DACL");
                }

                uint setResult = SetSecurityInfo(
                    handle,
                    SE_KERNEL_OBJECT,
                    DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                    IntPtr.Zero,
                    IntPtr.Zero,
                    desiredDacl,
                    IntPtr.Zero);
                if (setResult != 0)
                {
                    throw new Win32Exception((int)setResult, "set named-pipe DACL");
                }

                IntPtr ignoredOwner;
                IntPtr ignoredGroup;
                IntPtr ignoredDacl;
                IntPtr ignoredSacl;
                uint getResult = GetSecurityInfo(
                    handle,
                    SE_KERNEL_OBJECT,
                    DACL_SECURITY_INFORMATION,
                    out ignoredOwner,
                    out ignoredGroup,
                    out ignoredDacl,
                    out ignoredSacl,
                    out actualDescriptor);
                if (getResult != 0 || actualDescriptor == IntPtr.Zero)
                {
                    throw new Win32Exception((int)getResult, "read named-pipe DACL");
                }

                uint descriptorLength = GetSecurityDescriptorLength(actualDescriptor);
                if (descriptorLength == 0 || descriptorLength > 65536)
                {
                    throw new InvalidOperationException("invalid named-pipe descriptor length");
                }
                byte[] descriptorBytes = new byte[descriptorLength];
                Marshal.Copy(actualDescriptor, descriptorBytes, 0, (int)descriptorLength);
                RawSecurityDescriptor descriptor =
                    new RawSecurityDescriptor(descriptorBytes, 0);
                if ((descriptor.ControlFlags &
                     ControlFlags.DiscretionaryAclProtected) == 0)
                {
                    throw new InvalidOperationException("named-pipe DACL is not protected");
                }
                RawAcl acl = descriptor.DiscretionaryAcl;
                if (acl == null || acl.Count != 1)
                {
                    throw new InvalidOperationException(
                        "named-pipe DACL does not contain exactly one principal");
                }
                CommonAce ace = acl[0] as CommonAce;
                if (ace == null ||
                    ace.AceQualifier != AceQualifier.AccessAllowed ||
                    ace.AceFlags != AceFlags.None ||
                    !currentSid.Equals(ace.SecurityIdentifier) ||
                    (ace.AccessMask != GENERIC_ALL &&
                     ace.AccessMask != FILE_ALL_ACCESS))
                {
                    throw new InvalidOperationException(
                        "named-pipe DACL is not exact current-user full control");
                }
                return "{\"principal_count\":1,\"protected_dacl\":true," +
                    "\"windows_acl\":\"PROVEN\"}";
            }
            finally
            {
                if (actualDescriptor != IntPtr.Zero) LocalFree(actualDescriptor);
                if (desiredDescriptor != IntPtr.Zero) LocalFree(desiredDescriptor);
            }
        }
    }
}
'@

$pipePath = [Environment]::GetEnvironmentVariable(
  "DEEPLUNA_CANDIDATE_PIPE_ADDRESS",
  "Process"
)
if ([string]::IsNullOrWhiteSpace($pipePath)) {
  throw "candidate pipe address is unavailable"
}
[Console]::Out.Write(
  [DeepLunaCandidatePipeAcl]::ProtectAndAttest($pipePath)
)
`;

const CANDIDATE_PIPE_OWNER_POWERSHELL = String.raw`
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Add-Type -Language CSharp -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class DeepLunaCandidatePipeOwner
{
    private const uint GENERIC_READ = 0x80000000;
    private const uint GENERIC_WRITE = 0x40000000;
    private const uint OPEN_EXISTING = 3;
    private const uint SECURITY_SQOS_PRESENT = 0x00100000;
    private const uint SECURITY_ANONYMOUS = 0x00000000;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(
        string name,
        uint desiredAccess,
        uint shareMode,
        IntPtr securityAttributes,
        uint creationDisposition,
        uint flagsAndAttributes,
        IntPtr templateFile);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetNamedPipeServerProcessId(
        SafeFileHandle pipe,
        out uint serverProcessId);

    private static Exception Win32(string operation)
    {
        return new Win32Exception(Marshal.GetLastWin32Error(), operation);
    }

    public static string Read(string pipePath)
    {
        using (SafeFileHandle handle = CreateFileW(
            pipePath,
            GENERIC_READ | GENERIC_WRITE,
            0,
            IntPtr.Zero,
            OPEN_EXISTING,
            SECURITY_SQOS_PRESENT | SECURITY_ANONYMOUS,
            IntPtr.Zero))
        {
            if (handle.IsInvalid)
            {
                throw Win32("open named pipe for server PID");
            }
            uint processId;
            if (!GetNamedPipeServerProcessId(handle, out processId))
            {
                throw Win32("read named-pipe server PID");
            }
            if (processId == 0)
            {
                throw new InvalidOperationException(
                    "named-pipe server PID is unavailable");
            }
            return "{\"pipe_server_pid\":" + processId.ToString() + "}";
        }
    }
}
'@

$pipePath = [Environment]::GetEnvironmentVariable(
  "DEEPLUNA_CANDIDATE_PIPE_ADDRESS",
  "Process"
)
if ([string]::IsNullOrWhiteSpace($pipePath)) {
  throw "candidate pipe address is unavailable"
}
[Console]::Out.Write(
  [DeepLunaCandidatePipeOwner]::Read($pipePath)
)
`;

export function attestCandidateWindowsNamedPipeAcl(
  address,
  options = undefined,
) {
  if (
    process.platform !== "win32" ||
    typeof address !== "string" ||
    !/^\\\\\.\\pipe\\codex-deepluna-[0-9a-f]{20}-v[1-9][0-9]*$/.test(address) ||
    !address.endsWith(`-v${CANDIDATE_DAEMON_PROFILE.protocol}`)
  ) {
    throw new Error(CANDIDATE_PIPE_ACL_FAILURE);
  }
  let spawnSyncFunction;
  let systemRoot;
  let tempRoot;
  try {
    const captured = captureOwnData(
      options === undefined ? {} : options,
      new Set(["spawnSyncFunction", "systemRoot", "tempRoot"]),
    );
    spawnSyncFunction = captured.has("spawnSyncFunction")
      ? captured.get("spawnSyncFunction")
      : spawnSync;
    systemRoot = captured.has("systemRoot")
      ? captured.get("systemRoot")
      : (process.env.SystemRoot ?? "C:\\Windows");
    tempRoot = captured.has("tempRoot")
      ? captured.get("tempRoot")
      : (process.env.TEMP ?? process.env.TMP);
    if (
      typeof spawnSyncFunction !== "function" ||
      !validSystemRoot(systemRoot) ||
      typeof tempRoot !== "string" ||
      tempRoot.length === 0 ||
      tempRoot.includes("\0") ||
      !path.isAbsolute(tempRoot)
    ) {
      throw new TypeError();
    }
  } catch {
    throw new Error(CANDIDATE_PIPE_ACL_FAILURE);
  }

  const executable = path.win32.join(
    path.win32.normalize(systemRoot),
    "System32",
    "WindowsPowerShell",
    "v1.0",
    "powershell.exe",
  );
  let result;
  try {
    result = spawnSyncFunction(
      executable,
      [
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-OutputFormat",
        "Text",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        Buffer.from(CANDIDATE_PIPE_ACL_POWERSHELL, "utf16le").toString("base64"),
      ],
      {
        encoding: "utf8",
        env: {
          SystemRoot: systemRoot,
          WINDIR: systemRoot,
          TEMP: tempRoot,
          TMP: tempRoot,
          DEEPLUNA_CANDIDATE_PIPE_ADDRESS: address,
        },
        maxBuffer: MAX_CAPTURE_BYTES,
        shell: false,
        timeout: 15_000,
        windowsHide: true,
      },
    );
  } catch {
    throw new Error(CANDIDATE_PIPE_ACL_FAILURE);
  }

  try {
    if (
      result === null ||
      typeof result !== "object" ||
      result.status !== 0 ||
      result.error !== undefined ||
      typeof result.stdout !== "string" ||
      typeof result.stderr !== "string" ||
      result.stderr.trim() !== ""
    ) {
      throw new TypeError();
    }
    const evidence = JSON.parse(result.stdout);
    if (
      evidence === null ||
      typeof evidence !== "object" ||
      Array.isArray(evidence) ||
      Object.getPrototypeOf(evidence) !== Object.prototype ||
      Reflect.ownKeys(evidence).length !== 3 ||
      evidence.principal_count !== 1 ||
      evidence.protected_dacl !== true ||
      evidence.windows_acl !== "PROVEN"
    ) {
      throw new TypeError();
    }
    return Object.freeze({ ...evidence });
  } catch {
    throw new Error(CANDIDATE_PIPE_ACL_FAILURE);
  }
}

export function getCandidateWindowsNamedPipeServerProcessId(
  address,
  options = undefined,
) {
  if (
    process.platform !== "win32" ||
    typeof address !== "string" ||
    !/^\\\\\.\\pipe\\codex-deepluna-[0-9a-f]{20}-v[1-9][0-9]*$/.test(address) ||
    !address.endsWith(`-v${CANDIDATE_DAEMON_PROFILE.protocol}`)
  ) {
    throw new Error(CANDIDATE_PIPE_OWNER_FAILURE);
  }
  let spawnSyncFunction;
  let systemRoot;
  let tempRoot;
  try {
    const captured = captureOwnData(
      options === undefined ? {} : options,
      new Set(["spawnSyncFunction", "systemRoot", "tempRoot"]),
    );
    spawnSyncFunction = captured.has("spawnSyncFunction")
      ? captured.get("spawnSyncFunction")
      : spawnSync;
    systemRoot = captured.has("systemRoot")
      ? captured.get("systemRoot")
      : (process.env.SystemRoot ?? "C:\\Windows");
    tempRoot = captured.has("tempRoot")
      ? captured.get("tempRoot")
      : (process.env.TEMP ?? process.env.TMP);
    if (
      typeof spawnSyncFunction !== "function" ||
      !validSystemRoot(systemRoot) ||
      typeof tempRoot !== "string" ||
      tempRoot.length === 0 ||
      tempRoot.includes("\0") ||
      !path.isAbsolute(tempRoot)
    ) {
      throw new TypeError();
    }
  } catch {
    throw new Error(CANDIDATE_PIPE_OWNER_FAILURE);
  }
  const executable = path.win32.join(
    path.win32.normalize(systemRoot),
    "System32",
    "WindowsPowerShell",
    "v1.0",
    "powershell.exe",
  );
  let result;
  try {
    result = spawnSyncFunction(
      executable,
      [
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-OutputFormat",
        "Text",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        Buffer.from(CANDIDATE_PIPE_OWNER_POWERSHELL, "utf16le").toString(
          "base64",
        ),
      ],
      {
        encoding: "utf8",
        env: {
          SystemRoot: systemRoot,
          WINDIR: systemRoot,
          TEMP: tempRoot,
          TMP: tempRoot,
          DEEPLUNA_CANDIDATE_PIPE_ADDRESS: address,
        },
        maxBuffer: MAX_CAPTURE_BYTES,
        shell: false,
        timeout: 15_000,
        windowsHide: true,
      },
    );
  } catch {
    throw new Error(CANDIDATE_PIPE_OWNER_FAILURE);
  }
  try {
    if (
      result === null ||
      typeof result !== "object" ||
      result.status !== 0 ||
      result.error !== undefined ||
      typeof result.stdout !== "string" ||
      typeof result.stderr !== "string" ||
      result.stderr.trim() !== ""
    ) {
      throw new TypeError();
    }
    const evidence = JSON.parse(result.stdout);
    if (
      evidence === null ||
      typeof evidence !== "object" ||
      Array.isArray(evidence) ||
      Object.getPrototypeOf(evidence) !== Object.prototype ||
      Reflect.ownKeys(evidence).length !== 1 ||
      !Number.isSafeInteger(evidence.pipe_server_pid) ||
      evidence.pipe_server_pid < 1 ||
      evidence.pipe_server_pid > MAX_WINDOWS_PID
    ) {
      throw new TypeError();
    }
    return Object.freeze({
      address,
      processId: evidence.pipe_server_pid,
      status: "PROVEN",
    });
  } catch {
    throw new Error(CANDIDATE_PIPE_OWNER_FAILURE);
  }
}

function captureOwnData(value, allowedKeys) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError();
  }
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const captured = new Map();
  for (const key of Reflect.ownKeys(descriptors)) {
    if (typeof key !== "string" || !allowedKeys.has(key)) throw new TypeError();
    const descriptor = descriptors[key];
    if (
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError();
    }
    captured.set(key, descriptor.value);
  }
  return captured;
}

function captureStrictArray(value) {
  if (!Array.isArray(value)) throw new TypeError();
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const lengthDescriptor = descriptors.length;
  if (
    !lengthDescriptor ||
    !Object.hasOwn(lengthDescriptor, "value") ||
    !Number.isSafeInteger(lengthDescriptor.value) ||
    lengthDescriptor.value < 0
  ) {
    throw new TypeError();
  }

  const length = lengthDescriptor.value;
  const values = new Map();
  for (const key of Reflect.ownKeys(descriptors)) {
    if (key === "length") continue;
    if (typeof key !== "string" || !/^(0|[1-9]\d*)$/.test(key)) {
      throw new TypeError();
    }
    const index = Number(key);
    const descriptor = descriptors[key];
    if (
      !Number.isSafeInteger(index) ||
      index < 0 ||
      index >= length ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError();
    }
    values.set(index, descriptor.value);
  }
  if (values.size !== length) throw new TypeError();
  return Array.from({ length }, (_, index) => values.get(index));
}

function ownDataValue(value, key) {
  const descriptor = Object.getOwnPropertyDescriptor(value, key);
  if (!descriptor || !Object.hasOwn(descriptor, "value")) throw new TypeError();
  return descriptor.value;
}

function isPositiveSafeInteger(value) {
  return Number.isSafeInteger(value) && value > 0;
}

function isWindowsPid(value) {
  return (
    Number.isSafeInteger(value) &&
    value > 0 &&
    value <= MAX_WINDOWS_PID
  );
}

function validSystemRoot(value) {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    !/^[A-Za-z]:[\\/](?![\\/])/.test(value) ||
    /[\u0000-\u001f<>:"|?*]/.test(value.slice(2))
  ) {
    return false;
  }
  const segments = value.slice(3).split(/[\\/]/);
  return !segments.some((segment, index) => {
    if (segment === "." || segment === "..") return true;
    if (segment === "" && index !== segments.length - 1) return true;
    if (segment.endsWith(" ") || segment.endsWith(".")) return true;
    return /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(segment);
  });
}

function resultText(value) {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  if (Buffer.isBuffer(value)) return value.toString("utf8");
  throw new TypeError();
}

function exactAlreadyExitedRace(result, pid) {
  const descriptors = Object.getOwnPropertyDescriptors(result);
  const stdoutDescriptor = descriptors.stdout;
  const stderrDescriptor = descriptors.stderr;
  for (const descriptor of [stdoutDescriptor, stderrDescriptor]) {
    if (descriptor && !Object.hasOwn(descriptor, "value")) throw new TypeError();
  }
  const stdout = resultText(stdoutDescriptor?.value);
  const stderr = resultText(stderrDescriptor?.value);
  const expected = `the process "${pid}" not found.`;
  return `${stdout}\n${stderr}`
    .split(/\r?\n/)
    .map((line) => line.trim().toLowerCase().replace(/^error:\s*/, ""))
    .some((line) => line === expected);
}

export function killWindowsProcessTree(pid, options = undefined) {
  if (!isWindowsPid(pid)) throw new Error(INVALID_PROCESS_ID);

  let spawnSyncFunction;
  let systemRoot;
  try {
    const captured = captureOwnData(
      options === undefined ? {} : options,
      new Set(["spawnSyncFunction", "systemRoot"]),
    );
    spawnSyncFunction = captured.has("spawnSyncFunction")
      ? captured.get("spawnSyncFunction")
      : spawnSync;
    systemRoot = captured.has("systemRoot")
      ? captured.get("systemRoot")
      : (process.env.SystemRoot ?? "C:\\Windows");
    if (
      typeof spawnSyncFunction !== "function" ||
      !validSystemRoot(systemRoot)
    ) {
      throw new TypeError();
    }
  } catch {
    throw new Error(INVALID_PROCESS_TREE_OPTIONS);
  }

  const executable = path.win32.join(
    path.win32.normalize(systemRoot),
    "System32",
    "taskkill.exe",
  );
  let result;
  try {
    result = spawnSyncFunction(
      executable,
      ["/PID", String(pid), "/T", "/F"],
      { encoding: "utf8", shell: false, windowsHide: true },
    );
  } catch {
    throw new Error(PROCESS_TREE_FAILURE);
  }

  try {
    if (result === null || typeof result !== "object") throw new TypeError();
    const descriptors = Object.getOwnPropertyDescriptors(result);
    const statusDescriptor = descriptors.status;
    const errorDescriptor = descriptors.error;
    if (
      !statusDescriptor ||
      !Object.hasOwn(statusDescriptor, "value") ||
      (errorDescriptor &&
        (!Object.hasOwn(errorDescriptor, "value") ||
          errorDescriptor.value !== undefined))
    ) {
      throw new TypeError();
    }
    const status = statusDescriptor.value;
    if (
      status !== 0 &&
      !(status === 128 && exactAlreadyExitedRace(result, pid))
    ) {
      throw new TypeError();
    }
    return Object.freeze({ status, pid });
  } catch {
    throw new Error(PROCESS_TREE_FAILURE);
  }
}

function captureSupervisedOptions(options) {
  try {
    const captured = captureOwnData(
      options,
      new Set([
        "file",
        "args",
        "cwd",
        "timeoutMs",
        "signal",
        "spawnFunction",
        "killTree",
      ]),
    );
    const file = captured.get("file");
    const args = captured.has("args")
      ? captureStrictArray(captured.get("args"))
      : [];
    const cwd = captured.get("cwd");
    const timeoutMs = captured.get("timeoutMs");
    const signal = captured.get("signal");
    const spawnFunction = captured.has("spawnFunction")
      ? captured.get("spawnFunction")
      : spawn;
    const killTree = captured.has("killTree")
      ? captured.get("killTree")
      : (childPid) => Promise.resolve(killWindowsProcessTree(childPid));

    if (
      typeof file !== "string" ||
      file.trim().length === 0 ||
      file.includes("\0") ||
      typeof cwd !== "string" ||
      cwd.includes("\0") ||
      !path.isAbsolute(cwd) ||
      !Number.isSafeInteger(timeoutMs) ||
      timeoutMs < 1 ||
      timeoutMs > MAX_TIMER_DELAY_MS ||
      typeof spawnFunction !== "function" ||
      typeof killTree !== "function" ||
      (signal !== undefined && !(signal instanceof AbortSignal)) ||
      args.some((argument) => typeof argument !== "string" || argument.includes("\0"))
    ) {
      throw new TypeError();
    }

    return {
      file,
      args: Object.freeze([...args]),
      cwd,
      timeoutMs,
      signal,
      spawnFunction,
      killTree,
    };
  } catch {
    throw new Error(INVALID_SUPERVISED_OPTIONS);
  }
}

function boundedBufferAppend(existing, chunk) {
  let incoming;
  if (Buffer.isBuffer(chunk)) {
    incoming = chunk;
  } else if (typeof chunk === "string") {
    incoming = Buffer.from(chunk, "utf8");
  } else {
    throw new TypeError("invalid supervised output");
  }

  if (incoming.length >= MAX_CAPTURE_BYTES) {
    return Buffer.from(incoming.subarray(incoming.length - MAX_CAPTURE_BYTES));
  }
  const retainedBytes = MAX_CAPTURE_BYTES - incoming.length;
  const retained =
    existing.length <= retainedBytes
      ? existing
      : existing.subarray(existing.length - retainedBytes);
  return Buffer.concat([retained, incoming], retained.length + incoming.length);
}

function boundedUtf8Text(buffer) {
  let start = 0;
  while (start < buffer.length && (buffer[start] & 0xc0) === 0x80) {
    start += 1;
  }
  let text = buffer.subarray(start).toString("utf8");
  while (Buffer.byteLength(text, "utf8") > MAX_CAPTURE_BYTES) {
    const first = text.codePointAt(0);
    text = text.slice(first > 0xffff ? 2 : 1);
  }
  return text;
}

function closeRecord(code, closeSignal) {
  if (
    (code !== null && (!Number.isSafeInteger(code) || code < 0)) ||
    (closeSignal !== null && typeof closeSignal !== "string")
  ) {
    throw new Error("invalid supervised close result");
  }
  return { code, closeSignal };
}

function exactChildPid(child, initialPid) {
  let currentPid;
  try {
    currentPid = ownDataValue(child, "pid");
  } catch {
    throw new Error(INVALID_CHILD_PID);
  }
  if (
    !isWindowsPid(initialPid) ||
    !isWindowsPid(currentPid) ||
    currentPid !== initialPid
  ) {
    throw new Error(INVALID_CHILD_PID);
  }
  return currentPid;
}

function commandOutcome({
  reason,
  record,
  stdout,
  stderr,
  pid,
}) {
  let executionStatus;
  let exitCode;
  if (reason === "TIMEOUT") {
    executionStatus = "TIMEOUT";
    exitCode = 124;
  } else if (reason === "CANCELLED") {
    executionStatus = "CANCELLED";
    exitCode =
      record.code === null || record.code === 0 ? 130 : record.code;
  } else if (record.code === 0 && record.closeSignal === null) {
    executionStatus = "PASS";
    exitCode = 0;
  } else {
    executionStatus = "FAIL";
    exitCode = record.code === null ? 1 : record.code;
  }
  return Object.freeze({
    executionStatus,
    exitCode,
    signal: record.closeSignal,
    stdout: boundedUtf8Text(stdout),
    stderr: boundedUtf8Text(stderr),
    pid,
  });
}

export function runSupervisedCommand(options) {
  const command = captureSupervisedOptions(options);

  return new Promise((resolve, reject) => {
    let child;
    try {
      child = command.spawnFunction(command.file, command.args, {
        cwd: command.cwd,
        shell: false,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch (error) {
      reject(error instanceof Error ? error : new Error("supervised spawn failed"));
      return;
    }

    let stdoutStream;
    let stderrStream;
    let initialPid;
    try {
      if (!(child instanceof EventEmitter)) throw new TypeError();
      initialPid = ownDataValue(child, "pid");
      stdoutStream = ownDataValue(child, "stdout");
      stderrStream = ownDataValue(child, "stderr");
      if (
        (stdoutStream !== null &&
          stdoutStream !== undefined &&
          !(stdoutStream instanceof EventEmitter)) ||
        (stderrStream !== null &&
          stderrStream !== undefined &&
          !(stderrStream instanceof EventEmitter))
      ) {
        throw new TypeError();
      }
    } catch {
      reject(new Error("invalid supervised child process"));
      return;
    }

    let stdout = Buffer.alloc(0);
    let stderr = Buffer.alloc(0);
    let settled = false;
    let timer;
    let terminationReason = null;
    let killFinished = false;
    let observedClose = null;

    const removeAbortListener = () => {
      if (command.signal !== undefined) {
        AbortSignal.prototype.removeEventListener.call(
          command.signal,
          "abort",
          onAbort,
        );
      }
    };

    const cleanup = () => {
      if (timer !== undefined) clearTimeout(timer);
      removeAbortListener();
      EventEmitter.prototype.removeListener.call(child, "error", onError);
      EventEmitter.prototype.removeListener.call(child, "close", onClose);
      if (stdoutStream instanceof EventEmitter) {
        EventEmitter.prototype.removeListener.call(
          stdoutStream,
          "data",
          onStdout,
        );
      }
      if (stderrStream instanceof EventEmitter) {
        EventEmitter.prototype.removeListener.call(
          stderrStream,
          "data",
          onStderr,
        );
      }
    };

    const rejectOnce = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error instanceof Error ? error : new Error("supervised command failed"));
    };

    const resolveOnce = (reason, record) => {
      if (settled) return;
      let pid;
      let outcome;
      try {
        pid = exactChildPid(child, initialPid);
        outcome = commandOutcome({
          reason,
          record,
          stdout,
          stderr,
          pid,
        });
      } catch (error) {
        rejectOnce(error);
        return;
      }
      settled = true;
      cleanup();
      resolve(outcome);
    };

    const finishTermination = () => {
      if (!settled && killFinished && observedClose !== null) {
        resolveOnce(terminationReason, observedClose);
      }
    };

    const requestTermination = (reason) => {
      if (settled || terminationReason !== null) return;
      let pid;
      try {
        pid = exactChildPid(child, initialPid);
      } catch (error) {
        rejectOnce(error);
        return;
      }
      terminationReason = reason;
      if (timer !== undefined) clearTimeout(timer);
      removeAbortListener();

      let termination;
      try {
        termination = command.killTree(pid);
      } catch (error) {
        rejectOnce(error);
        return;
      }
      Promise.resolve(termination).then(
        () => {
          if (settled) return;
          killFinished = true;
          finishTermination();
        },
        (error) => rejectOnce(error),
      );
    };

    function onStdout(chunk) {
      try {
        stdout = boundedBufferAppend(stdout, chunk);
      } catch (error) {
        rejectOnce(error);
      }
    }

    function onStderr(chunk) {
      try {
        stderr = boundedBufferAppend(stderr, chunk);
      } catch (error) {
        rejectOnce(error);
      }
    }

    function onError(error) {
      rejectOnce(error);
    }

    function onClose(code, closeSignal) {
      if (settled) return;
      let record;
      try {
        record = closeRecord(code, closeSignal);
      } catch (error) {
        rejectOnce(error);
        return;
      }
      if (terminationReason === null) {
        resolveOnce(null, record);
        return;
      }
      observedClose = record;
      finishTermination();
    }

    function onAbort() {
      requestTermination("CANCELLED");
    }

    EventEmitter.prototype.once.call(child, "error", onError);
    EventEmitter.prototype.once.call(child, "close", onClose);
    if (stdoutStream instanceof EventEmitter) {
      EventEmitter.prototype.on.call(stdoutStream, "data", onStdout);
    }
    if (stderrStream instanceof EventEmitter) {
      EventEmitter.prototype.on.call(stderrStream, "data", onStderr);
    }
    timer = setTimeout(() => requestTermination("TIMEOUT"), command.timeoutMs);
    if (command.signal !== undefined) {
      AbortSignal.prototype.addEventListener.call(
        command.signal,
        "abort",
        onAbort,
        { once: true },
      );
      if (command.signal.aborted) onAbort();
    }
  });
}

export function runSupervisedApprovedCommand(command, options = undefined) {
  if (typeof command !== "string" || command.trim().length === 0) {
    throw new Error("approved command must be a non-empty string");
  }
  const approvedCommand = command.trim();
  const shell = process.platform === "win32"
    ? Object.freeze({
      file: "powershell.exe",
      args: Object.freeze(["-NoProfile", "-NoLogo", "-NonInteractive", "-Command", approvedCommand]),
    })
    : Object.freeze({
      file: "sh",
      args: Object.freeze(["-lc", approvedCommand]),
    });

  return runSupervisedCommand({
    file: shell.file,
    args: shell.args,
    ...options,
  });
}

function captureShardInputs(nodeIds, options) {
  try {
    const nodes = captureStrictArray(nodeIds);
    const captured = captureOwnData(
      options === undefined ? {} : options,
      new Set(["maximumItems", "workers"]),
    );
    const maximumItems = captured.has("maximumItems")
      ? captured.get("maximumItems")
      : 10;
    const workers = captured.has("workers") ? captured.get("workers") : 4;
    if (
      nodes.length === 0 ||
      !Number.isSafeInteger(maximumItems) ||
      maximumItems < 1 ||
      maximumItems > 10 ||
      !isPositiveSafeInteger(workers) ||
      workers > MAX_PYTEST_WORKERS ||
      nodes.some(
        (nodeId) =>
          typeof nodeId !== "string" ||
          nodeId.trim().length === 0 ||
          nodeId.trim() !== nodeId ||
          nodeId.includes("\0"),
      )
    ) {
      throw new TypeError();
    }
    return { nodes, maximumItems, workers };
  } catch {
    throw new Error(INVALID_SHARD_INPUT);
  }
}

export function buildPytestShards(nodeIds, options = undefined) {
  const { nodes, maximumItems, workers } = captureShardInputs(nodeIds, options);
  const unique = [];
  const seen = new Set();
  for (const nodeId of nodes) {
    if (seen.has(nodeId)) continue;
    seen.add(nodeId);
    unique.push(nodeId);
  }

  const shards = [];
  for (let index = 0; index < unique.length; index += maximumItems) {
    const nodeIdGroup = Object.freeze(
      unique.slice(index, index + maximumItems),
    );
    const args = Object.freeze([
      "-m",
      "pytest",
      ...nodeIdGroup,
      "-n",
      String(workers),
      "--dist=load",
      "--max-worker-restart=0",
      "-q",
      "--tb=short",
      "--durations=10",
    ]);
    shards.push(
      Object.freeze({
        nodeIds: nodeIdGroup,
        file: ".\\.venv\\Scripts\\python.exe",
        args,
      }),
    );
  }
  return Object.freeze(shards);
}

export const DAEMON_PROTOCOL_VERSION = 1;

const MAX_DAEMON_FRAME_BYTES = 64 * 1024;
const MAX_DAEMON_PROJECT_ID = 256;
const MAX_DAEMON_REQUEST_ID = 256;
const MAX_DAEMON_TYPE = 64;
const MAX_DAEMON_PENDING_REQUESTS = 128;
const DEFAULT_MAX_DAEMON_CONNECTIONS = 128;
const DEFAULT_DAEMON_TIMEOUT_MS = 2000;
const DEFAULT_DISPATCH_INTERVAL_MS = 250;
const DEFAULT_LEASE_MS = 60_000;
const ACTIVATION_STATUS = Object.freeze({
  hmacRequired: true,
  windowsAcl: "UNPROVEN",
  productionActivationEligible: false,
});

function daemonError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

export function enqueueCandidateOriginFairJob(scheduler, originId, job) {
  if (
    scheduler === null ||
    (typeof scheduler !== "object" && typeof scheduler !== "function") ||
    typeof scheduler.enqueue !== "function" ||
    !isPositiveSafeInteger(originId)
  ) {
    throw new TypeError("invalid candidate origin scheduler input");
  }
  const allowedKeys = new Set([
    "jobId",
    "taskId",
    "poolId",
    "priority",
    "createdAtMs",
    "role",
  ]);
  let captured;
  try {
    captured = captureOwnData(job, allowedKeys);
  } catch {
    throw new TypeError("invalid candidate origin scheduler job");
  }
  for (const key of ["jobId", "poolId", "priority", "createdAtMs"]) {
    if (!captured.has(key)) {
      throw new TypeError("invalid candidate origin scheduler job");
    }
  }
  const originJob = {
    jobId: captured.get("jobId"),
    taskId: `origin:${originId}`,
    poolId: captured.get("poolId"),
    priority: captured.get("priority"),
    createdAtMs: captured.get("createdAtMs"),
  };
  if (captured.has("role")) originJob.role = captured.get("role");
  return scheduler.enqueue(originJob);
}

export async function establishCandidateOriginSession(options) {
  const optionKeys = new Set([
    "secret",
    "clientHello",
    "store",
    "capabilityVerifier",
    "serverNonce",
    "serverInstanceId",
  ]);
  let capturedOptions;
  try {
    capturedOptions = captureOwnData(options, optionKeys);
  } catch {
    throw new TypeError("invalid candidate origin session options");
  }
  if (
    capturedOptions.size !== optionKeys.size ||
    [...optionKeys].some((key) => !capturedOptions.has(key))
  ) {
    throw new TypeError("invalid candidate origin session options");
  }

  const store = capturedOptions.get("store");
  const capabilityVerifier = capturedOptions.get("capabilityVerifier");
  let authenticateCandidateOrigin;
  try {
    let owner = store;
    for (let depth = 0; depth < 8 && owner !== null; depth += 1) {
      const descriptor = Object.getOwnPropertyDescriptor(
        owner,
        "authenticateCandidateOrigin",
      );
      if (descriptor !== undefined) {
        if (
          !Object.hasOwn(descriptor, "value") ||
          typeof descriptor.value !== "function"
        ) {
          throw new TypeError();
        }
        authenticateCandidateOrigin = descriptor.value;
        break;
      }
      owner = Object.getPrototypeOf(owner);
    }
  } catch {
    throw new TypeError("invalid candidate origin session dependencies");
  }
  if (
    store === null ||
    (typeof store !== "object" && typeof store !== "function") ||
    typeof authenticateCandidateOrigin !== "function" ||
    typeof capabilityVerifier !== "function"
  ) {
    throw new TypeError("invalid candidate origin session dependencies");
  }

  const helloKeys = new Set([
    "protocol",
    "rpcSchema",
    "projectId",
    "originThreadHash",
    "originCapabilityHash",
    "clientRelease",
    "runtimeBuildHash",
    "clientNonce",
    "requiredCapabilities",
    "mac",
  ]);
  let clientHello;
  try {
    const capturedHello = captureOwnData(
      capturedOptions.get("clientHello"),
      helloKeys,
    );
    if (
      capturedHello.size !== helloKeys.size ||
      [...helloKeys].some((key) => !capturedHello.has(key))
    ) {
      throw new TypeError();
    }
    clientHello = Object.freeze({
      protocol: capturedHello.get("protocol"),
      rpcSchema: capturedHello.get("rpcSchema"),
      projectId: capturedHello.get("projectId"),
      originThreadHash: capturedHello.get("originThreadHash"),
      originCapabilityHash: capturedHello.get("originCapabilityHash"),
      clientRelease: capturedHello.get("clientRelease"),
      runtimeBuildHash: capturedHello.get("runtimeBuildHash"),
      clientNonce: capturedHello.get("clientNonce"),
      requiredCapabilities: Object.freeze(
        captureStrictArray(capturedHello.get("requiredCapabilities")),
      ),
      mac: capturedHello.get("mac"),
    });
  } catch {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }
  if (!verifyCandidateClientHello(capturedOptions.get("secret"), clientHello)) {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }

  const claim = Object.freeze({
    projectId: clientHello.projectId,
    originThreadHash: clientHello.originThreadHash,
    originCapabilityHash: clientHello.originCapabilityHash,
  });
  try {
    if ((await capabilityVerifier(claim)) !== true) {
      throw daemonError("AUTH_FAILED", "authentication failed");
    }
  } catch {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }

  let capturedOrigin;
  try {
    const origin = await Reflect.apply(authenticateCandidateOrigin, store, [claim]);
    const originKeys = new Set([
      "originId",
      "projectId",
      "originThreadHash",
      "originCapabilityHash",
    ]);
    capturedOrigin = captureOwnData(origin, originKeys);
    if (
      capturedOrigin.size !== originKeys.size ||
      [...originKeys].some((key) => !capturedOrigin.has(key))
    ) {
      throw new TypeError();
    }
  } catch {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }
  if (
    !Number.isSafeInteger(capturedOrigin.get("originId")) ||
    capturedOrigin.get("originId") < 1 ||
    capturedOrigin.get("projectId") !== claim.projectId ||
    capturedOrigin.get("originThreadHash") !== claim.originThreadHash ||
    capturedOrigin.get("originCapabilityHash") !== claim.originCapabilityHash
  ) {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }

  let serverHello;
  try {
    serverHello = createCandidateServerHello(
      capturedOptions.get("secret"),
      clientHello,
      {
        serverNonce: capturedOptions.get("serverNonce"),
        serverInstanceId: capturedOptions.get("serverInstanceId"),
        serverStartedAtMs: CANDIDATE_PROCESS_STARTED_AT_MS,
        runtimeBuildHash: CANDIDATE_RUNTIME_BUILD_HASH,
        originId: capturedOrigin.get("originId"),
      },
    );
  } catch {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }
  const session = Object.freeze({
    originId: capturedOrigin.get("originId"),
    projectId: claim.projectId,
    originThreadHash: claim.originThreadHash,
    originCapabilityHash: claim.originCapabilityHash,
    serverHello,
  });
  AUTHENTICATED_CANDIDATE_ORIGIN_SESSIONS.add(session);
  return session;
}

function candidateDependencyMethod(target, name) {
  try {
    let owner = target;
    for (let depth = 0; depth < 8 && owner !== null; depth += 1) {
      const descriptor = Object.getOwnPropertyDescriptor(owner, name);
      if (descriptor !== undefined) {
        if (
          !Object.hasOwn(descriptor, "value") ||
          typeof descriptor.value !== "function"
        ) {
          throw new TypeError();
        }
        return descriptor.value;
      }
      owner = Object.getPrototypeOf(owner);
    }
  } catch {
    throw new TypeError("invalid candidate origin API dependency");
  }
  throw new TypeError("invalid candidate origin API dependency");
}

function capturedCandidateApiRequest(value, allowedKeys, requiredKeys) {
  let captured;
  try {
    captured = captureOwnData(value, allowedKeys);
  } catch {
    throw new TypeError("invalid candidate origin API request");
  }
  if (
    requiredKeys.some((key) => !captured.has(key)) ||
    [...captured.keys()].some((key) => !allowedKeys.has(key))
  ) {
    throw new TypeError("invalid candidate origin API request");
  }
  return captured;
}

export function createCandidateOriginBoundApi(options) {
  const capturedOptions = capturedCandidateApiRequest(
    options,
    new Set(["session", "store", "cancelWhenUnobserved"]),
    ["session", "store"],
  );
  const session = capturedOptions.get("session");
  const store = capturedOptions.get("store");
  const cancelWhenUnobserved = capturedOptions.has("cancelWhenUnobserved")
    ? capturedOptions.get("cancelWhenUnobserved")
    : false;
  if (typeof cancelWhenUnobserved !== "boolean") {
    throw new TypeError("invalid candidate origin API request");
  }
  if (!AUTHENTICATED_CANDIDATE_ORIGIN_SESSIONS.has(session)) {
    throw daemonError("AUTH_FAILED", "authentication failed");
  }
  const methods = Object.fromEntries(
    [
      "enqueueCandidateJob",
      "submitCandidateWorker",
      "getCandidateGeneration",
      "getCandidateWorkerStatus",
      "detachCandidateWorker",
      "cancelCandidateWorker",
      "recordCandidateSolPlan",
      "submitCandidateHead",
      "getCandidateHeadStatus",
      "cancelCandidateHead",
      "getCandidateHeadMetrics",
      "getCandidateBatchStatus",
      "getCandidateBatchMetrics",
      "getCandidateStoreSchemaVersion",
      "listCandidateEvents",
      "cancelCandidateGeneration",
      "getCandidateOriginMetrics",
      "getCandidateProjectMetrics",
      "acquireCandidateWriterAdmission",
      "assertCandidateWriterFence",
      "releaseCandidateWriterAdmission",
    ].map((name) => [name, candidateDependencyMethod(store, name)]),
  );
  const scope = Object.freeze({
    originId: session.originId,
    projectId: session.projectId,
  });
  const invoke = (name, request) =>
    Reflect.apply(methods[name], store, [request]);
  const publicWorkerClaims =
    invoke("getCandidateStoreSchemaVersion", undefined) >= 4;
  return Object.freeze({
    submit(request) {
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["contract"]),
        ["contract"],
      );
      if (!publicWorkerClaims) {
        return invoke("enqueueCandidateJob", {
          originId: scope.originId,
          contract: captured.get("contract"),
        });
      }
      const submitted = invoke("submitCandidateWorker", {
        originId: scope.originId,
        contract: captured.get("contract"),
      });
      return Object.freeze({
        schema_version: submitted.schema_version,
        job_id: submitted.jobId,
        status: submitted.status,
        execution_status: submitted.execution_status,
        evidence_verdict: submitted.evidence_verdict,
        cache_hit: submitted.cache_hit,
        coalesced: submitted.coalesced,
      });
    },
    status(request) {
      if (publicWorkerClaims) {
        const captured = capturedCandidateApiRequest(
          request,
          new Set(["jobId"]),
          ["jobId"],
        );
        return invoke("getCandidateWorkerStatus", {
          ...scope,
          jobId: captured.get("jobId"),
        });
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId", "generation"]),
        ["jobId", "generation"],
      );
      return invoke("getCandidateGeneration", {
        ...scope,
        jobId: captured.get("jobId"),
        generation: captured.get("generation"),
      });
    },
    detach(request) {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate detach requires schema v4",
        );
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId"]),
        ["jobId"],
      );
      return invoke("detachCandidateWorker", {
        ...scope,
        jobId: captured.get("jobId"),
      });
    },
    events(request) {
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId", "afterSequence", "limit"]),
        ["jobId"],
      );
      const scoped = { ...scope, jobId: captured.get("jobId") };
      if (captured.has("afterSequence")) {
        scoped.afterSequence = captured.get("afterSequence");
      }
      if (captured.has("limit")) scoped.limit = captured.get("limit");
      return invoke("listCandidateEvents", scoped);
    },
    cancel(request) {
      if (publicWorkerClaims) {
        const captured = capturedCandidateApiRequest(
          request,
          new Set(["jobId"]),
          ["jobId"],
        );
        return invoke("cancelCandidateWorker", {
          ...scope,
          jobId: captured.get("jobId"),
          cancelWhenUnobserved,
        });
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId", "generation", "actor", "reason"]),
        ["jobId", "generation", "actor", "reason"],
      );
      return invoke("cancelCandidateGeneration", {
        ...scope,
        jobId: captured.get("jobId"),
        generation: captured.get("generation"),
        actor: captured.get("actor"),
        reason: captured.get("reason"),
      });
    },
    metrics() {
      const metrics = invoke("getCandidateOriginMetrics", scope);
      if (!publicWorkerClaims) return metrics;
      return Object.freeze({
        schema_version: 1,
        total_jobs: metrics.totalJobs,
        queued_jobs: metrics.queuedJobs,
        running_jobs: metrics.runningJobs,
        validating_jobs: metrics.validatingJobs,
        terminal_jobs: metrics.terminalJobs,
        provider_transmissions: metrics.costReservationCount,
        input_tokens: metrics.inputTokens,
        cached_input_tokens: metrics.cachedInputTokens,
        output_tokens: metrics.outputTokens,
        total_tokens: metrics.totalTokens,
        spent_nano_usd: metrics.actualNanoUsd,
        reserved_nano_usd: metrics.openReservedNanoUsd,
        unknown_transmissions: metrics.unknownCostReservations,
      });
    },
    projectMetrics() {
      return invoke("getCandidateProjectMetrics", scope);
    },
    headPlan(request) {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate head planning requires schema v4",
        );
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["plan"]),
        ["plan"],
      );
      return invoke("recordCandidateSolPlan", {
        ...scope,
        plan: captured.get("plan"),
      });
    },
    headSubmit(request) {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate head submission requires schema v4",
        );
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["planId"]),
        ["planId"],
      );
      const submitted = invoke("submitCandidateHead", {
        ...scope,
        planId: captured.get("planId"),
      });
      return Object.freeze({
        schema_version: submitted.schema_version,
        job_id: submitted.jobId,
        status: submitted.status,
        execution_status: submitted.execution_status,
        evidence_verdict: submitted.evidence_verdict,
        cache_hit: submitted.cache_hit,
        coalesced: submitted.coalesced,
        plan_id: submitted.plan_id,
        requested_effort: submitted.requested_effort,
      });
    },
    headStatus(request) {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate head status requires schema v4",
        );
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId"]),
        ["jobId"],
      );
      return invoke("getCandidateHeadStatus", {
        ...scope,
        jobId: captured.get("jobId"),
      });
    },
    headMetrics() {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate head metrics require schema v4",
        );
      }
      return invoke("getCandidateHeadMetrics", scope);
    },
    headCancel(request) {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate head cancellation requires schema v4",
        );
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId"]),
        ["jobId"],
      );
      return invoke("cancelCandidateHead", {
        ...scope,
        jobId: captured.get("jobId"),
        cancelWhenUnobserved,
      });
    },
    batchStatus(request) {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate batch status requires schema v4",
        );
      }
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["batchId"]),
        ["batchId"],
      );
      return invoke("getCandidateBatchStatus", {
        ...scope,
        batchId: captured.get("batchId"),
      });
    },
    batchMetrics() {
      if (!publicWorkerClaims) {
        throw daemonError(
          "CAPABILITY_MISMATCH",
          "candidate batch metrics require schema v4",
        );
      }
      return invoke("getCandidateBatchMetrics", scope);
    },
    acquireWriter(request) {
      const captured = capturedCandidateApiRequest(
        request,
        new Set([
          "jobId",
          "generation",
          "leaseEpoch",
          "worktreeRoot",
          "outputPaths",
        ]),
        [
          "jobId",
          "generation",
          "leaseEpoch",
          "worktreeRoot",
          "outputPaths",
        ],
      );
      return invoke("acquireCandidateWriterAdmission", {
        ...scope,
        jobId: captured.get("jobId"),
        generation: captured.get("generation"),
        leaseEpoch: captured.get("leaseEpoch"),
        worktreeRoot: captured.get("worktreeRoot"),
        outputPaths: captured.get("outputPaths"),
      });
    },
    assertWriterFence(request) {
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId", "generation", "leaseEpoch", "fencingToken"]),
        ["jobId", "generation", "leaseEpoch", "fencingToken"],
      );
      return invoke("assertCandidateWriterFence", {
        ...scope,
        jobId: captured.get("jobId"),
        generation: captured.get("generation"),
        leaseEpoch: captured.get("leaseEpoch"),
        fencingToken: captured.get("fencingToken"),
      });
    },
    releaseWriter(request) {
      const captured = capturedCandidateApiRequest(
        request,
        new Set(["jobId", "generation", "leaseEpoch", "fencingToken"]),
        ["jobId", "generation", "leaseEpoch", "fencingToken"],
      );
      return invoke("releaseCandidateWriterAdmission", {
        ...scope,
        jobId: captured.get("jobId"),
        generation: captured.get("generation"),
        leaseEpoch: captured.get("leaseEpoch"),
        fencingToken: captured.get("fencingToken"),
      });
    },
  });
}

function candidateInactiveHeadPlanProjection(planPayload, input, session) {
  const canonicalPlan = canonicalCandidateDaemonJson(planPayload);
  const plan = JSON.parse(canonicalPlan);
  if (
    plan.project_id !== session.projectId ||
    plan.originThreadHash !== session.originThreadHash ||
    plan.originCapabilityHash !== session.originCapabilityHash ||
    typeof plan.plan_id !== "string" ||
    !/^SRP-[a-f0-9]{32}$/.test(plan.plan_id) ||
    plan.schema_version !== 1 ||
    plan.route === null ||
    typeof plan.route !== "object" ||
    Array.isArray(plan.route)
  ) {
    throw daemonError(
      "CAPABILITY_MISMATCH",
      "candidate Sol plan does not match the authenticated scope",
    );
  }
  const reasonCodes = plan.route.reasons.map((reason) => {
    if (
      /^Reasoning score [0-9]+ selected (?:medium|high|xhigh)\.$/.test(reason)
    ) {
      return "reasoning-score";
    }
    if (
      reason ===
      `Authority floor requires xhigh: ${plan.route.authority_domains.join(", ")}.`
    ) {
      return "authority-domain";
    }
    if (reason === "Every one-shot Max escalation gate is satisfied.") {
      return "max-one-shot-eligible";
    }
    if (reason === "The active effort already matches the selected effort.") {
      return "active-effort-matches";
    }
    if (
      reason ===
      "A separate lower-effort job would cost more than handling this small task now."
    ) {
      return "delegation-overhead-dominates";
    }
    if (reason === "Deterministic mechanical work is eligible for DeepLuna.") {
      return "deterministic-deepluna-eligible";
    }
    throw daemonError(
      "CAPABILITY_MISMATCH",
      "candidate Sol plan contains an unknown route reason",
    );
  });
  const digest = (value) =>
    crypto
      .createHash("sha256")
      .update(canonicalCandidateDaemonJson(value))
      .digest("hex");
  return Object.freeze({
    schema_version: 1,
    plan_id: plan.plan_id,
    decision: plan.route.action,
    selected_effort: plan.route.selected_effort,
    reasons: Object.freeze(reasonCodes),
    max_eligible: plan.route.max_eligible,
    attempt_fingerprint: digest({
      project_id: plan.project_id,
      output_schema_hash: plan.output_schema_hash,
      provider: plan.provider,
      model: plan.model,
      selected_effort: plan.route.selected_effort,
      policy_hash: plan.policy_hash,
      evidence_hash: plan.evidence_hash,
      governance_hash: plan.governance_hash,
      route_contract: plan.route_contract,
      task: plan.task,
    }),
    input_fingerprint: digest(input),
    cache_eligible: plan.task.reuseCache === true,
    policy_hash: plan.policy_hash,
    evidence_hash: plan.evidence_hash,
    governance_hash: plan.governance_hash,
    plan_payload: plan,
  });
}

export function createCandidateInactiveHeadRpcHandlers(options) {
  const captured = capturedCandidateApiRequest(
    options,
    new Set(["headManager"]),
    ["headManager"],
  );
  const headManager = captured.get("headManager");
  const planHead = candidateDependencyMethod(headManager, "plan");
  const loadPlan = candidateDependencyMethod(headManager, "loadPlan");
  const assertCurrentInputs = candidateDependencyMethod(
    headManager,
    "assertCurrentInputs",
  );
  const prepareHeadPlan = async (context) => {
    const request = capturedCandidateApiRequest(
      context,
      new Set(["api", "method", "payload", "session"]),
      ["method", "payload", "session"],
    );
    if (request.get("method") !== "head.plan") {
      throw daemonError("INVALID_REQUEST", "request rejected");
    }
    const payload = capturedCandidateApiRequest(
      request.get("payload"),
      new Set(["input"]),
      ["input"],
    );
    const planned = await Reflect.apply(planHead, headManager, [
      payload.get("input"),
    ]);
    const summary = capturedCandidateApiRequest(
      planned,
      new Set([
        "plan_id",
        "evidence_id",
        "action",
        "switch_scope",
        "selected_effort",
        "policy_hash",
        "evidence_hash",
        "governance_hash",
        "provider_calls",
      ]),
      [
        "plan_id",
        "evidence_id",
        "action",
        "switch_scope",
        "selected_effort",
        "policy_hash",
        "evidence_hash",
        "governance_hash",
        "provider_calls",
      ],
    );
    if (
      summary.get("provider_calls") !== 0 ||
      summary.get("evidence_id") !== summary.get("plan_id")
    ) {
      throw daemonError(
        "CAPABILITY_MISMATCH",
        "candidate planning crossed the provider-free boundary",
      );
    }
    const planPayload = Reflect.apply(loadPlan, headManager, [
      summary.get("plan_id"),
    ]);
    const projection = candidateInactiveHeadPlanProjection(
      planPayload,
      payload.get("input"),
      request.get("session"),
    );
    if (
      projection.decision !== summary.get("action") ||
      projection.selected_effort !== summary.get("selected_effort") ||
      projection.policy_hash !== summary.get("policy_hash") ||
      projection.evidence_hash !== summary.get("evidence_hash") ||
      projection.governance_hash !== summary.get("governance_hash")
    ) {
      throw daemonError(
        "CAPABILITY_MISMATCH",
        "candidate Sol plan summary conflicts with its artifact",
      );
    }
    return projection;
  };
  const prepareHeadSubmit = async (context) => {
    const request = capturedCandidateApiRequest(
      context,
      new Set(["api", "method", "payload", "session"]),
      ["method", "payload", "session"],
    );
    if (request.get("method") !== "head.submit") {
      throw daemonError("INVALID_REQUEST", "request rejected");
    }
    const payload = capturedCandidateApiRequest(
      request.get("payload"),
      new Set(["planId"]),
      ["planId"],
    );
    const planPayload = Reflect.apply(loadPlan, headManager, [
      payload.get("planId"),
    ]);
    candidateInactiveHeadPlanProjection(
      planPayload,
      { plan_id: payload.get("planId") },
      request.get("session"),
    );
    await Reflect.apply(assertCurrentInputs, headManager, [planPayload]);
    return Object.freeze({ planId: payload.get("planId") });
  };
  return Object.freeze({
    prepareHeadPlan,
    prepareHeadSubmit,
    headPlan(context) {
      const request = capturedCandidateApiRequest(
        context,
        new Set(["api", "method", "payload", "prepared", "session"]),
        ["api", "method", "payload", "session"],
      );
      if (request.has("prepared")) {
        return request.get("api").headPlan({ plan: request.get("prepared") });
      }
      return prepareHeadPlan(context).then((prepared) =>
        request.get("api").headPlan({ plan: prepared })
      );
    },
    headSubmit(context) {
      const request = capturedCandidateApiRequest(
        context,
        new Set(["api", "method", "payload", "prepared", "session"]),
        ["api", "method", "payload", "session"],
      );
      if (request.has("prepared")) {
        return request.get("api").headSubmit({
          planId: request.get("prepared").planId,
        });
      }
      return prepareHeadSubmit(context).then((prepared) =>
        request.get("api").headSubmit({ planId: prepared.planId })
      );
    },
  });
}

const CANDIDATE_V2_PUBLIC_ERRORS = Object.freeze({
  ACTIVATION_DISABLED: Object.freeze({
    code: "ACTIVATION_DISABLED",
    message: "daemon activation is disabled",
    retryable: false,
  }),
  AUTH_FAILED: Object.freeze({
    code: "AUTH_FAILED",
    message: "authentication failed",
    retryable: false,
  }),
  CAPABILITY_MISMATCH: Object.freeze({
    code: "CAPABILITY_MISMATCH",
    message: "capability mismatch",
    retryable: false,
  }),
  DAEMON_BUSY: Object.freeze({
    code: "DAEMON_BUSY",
    message: "daemon capacity is busy",
    retryable: true,
  }),
  DAEMON_TIMEOUT: Object.freeze({
    code: "DAEMON_TIMEOUT",
    message: "daemon request timed out",
    retryable: true,
  }),
  INTERNAL_ERROR: Object.freeze({
    code: "INTERNAL_ERROR",
    message: "daemon request failed",
    retryable: false,
  }),
  INVALID_REQUEST: Object.freeze({
    code: "INVALID_REQUEST",
    message: "request rejected",
    retryable: false,
  }),
  JOB_TERMINAL: Object.freeze({
    code: "JOB_TERMINAL",
    message: "job is terminal",
    retryable: false,
  }),
  MAX_ATTEMPT_EXHAUSTED: Object.freeze({
    code: "MAX_ATTEMPT_EXHAUSTED",
    message: "maximum effort attempt is exhausted",
    retryable: false,
  }),
  NOT_FOUND_OR_NOT_OWNED: Object.freeze({
    code: "NOT_FOUND_OR_NOT_OWNED",
    message: "resource not found",
    retryable: false,
  }),
  PROTOCOL_MISMATCH: Object.freeze({
    code: "PROTOCOL_MISMATCH",
    message: "protocol mismatch",
    retryable: false,
  }),
  REQUEST_ID_CONFLICT: Object.freeze({
    code: "REQUEST_ID_CONFLICT",
    message: "request conflicts with durable identity",
    retryable: false,
  }),
  REQUEST_IN_PROGRESS: Object.freeze({
    code: "REQUEST_IN_PROGRESS",
    message: "request is in progress",
    retryable: true,
  }),
  REQUEST_TOO_LARGE: Object.freeze({
    code: "REQUEST_TOO_LARGE",
    message: "request exceeds the allowed size",
    retryable: false,
  }),
  UNKNOWN_METHOD: Object.freeze({
    code: "UNKNOWN_METHOD",
    message: "unknown request method",
    retryable: false,
  }),
});

function candidateV2PublicError(error) {
  const mappedCode =
    typeof error?.code === "string" &&
    Object.hasOwn(CANDIDATE_V2_PUBLIC_ERRORS, error.code)
      ? error.code
      : error?.code === "ORIGIN_QUEUE_LIMIT" ||
          error?.code === "GLOBAL_QUEUE_LIMIT" ||
          error?.code === "ACTIVE_ORIGIN_LIMIT"
        ? "DAEMON_BUSY"
        : error instanceof TypeError
          ? "INVALID_REQUEST"
          : "INTERNAL_ERROR";
  return CANDIDATE_V2_PUBLIC_ERRORS[mappedCode];
}

function parseCandidateV2Frame(line, maximumBytes) {
  if (
    typeof line !== "string" ||
    Buffer.byteLength(line, "utf8") > maximumBytes
  ) {
    throw daemonError("REQUEST_TOO_LARGE", "request rejected");
  }
  let parsed;
  try {
    parsed = JSON.parse(line);
    canonicalCandidateDaemonJson(parsed);
  } catch {
    throw daemonError("INVALID_REQUEST", "request rejected");
  }
  return parsed;
}

function closeCandidateV2Socket(socket) {
  try {
    if (!socket.destroyed) socket.destroy();
  } catch {
    // Candidate transport cleanup is best effort and never mutates durable state.
  }
}

function createCandidateV2LineChannel(socket) {
  const bufferedLines = [];
  const readers = [];
  let failure = null;
  let stopped = false;
  let removeReader = () => {};
  const fail = (error) => {
    if (failure !== null) return;
    failure = error;
    removeReader();
    while (readers.length !== 0) {
      const reader = readers.shift();
      clearTimeout(reader.timer);
      reader.reject(error);
    }
    bufferedLines.length = 0;
  };
  removeReader = attachBoundedFrameReader(
    socket,
    async (line) => {
      if (readers.length !== 0) {
        const reader = readers.shift();
        clearTimeout(reader.timer);
        reader.resolve(line);
        return;
      }
      if (bufferedLines.length >= 16) {
        fail(daemonError("INVALID_REQUEST", "request rejected"));
        closeCandidateV2Socket(socket);
        return;
      }
      bufferedLines.push(line);
    },
    () => {
      fail(daemonError("INVALID_REQUEST", "request rejected"));
      closeCandidateV2Socket(socket);
    },
  );
  const onClose = () =>
    fail(daemonError("DAEMON_TRANSPORT", "daemon transport closed"));
  const onError = () =>
    fail(daemonError("DAEMON_TRANSPORT", "daemon transport failed"));
  socket.once("close", onClose);
  socket.once("error", onError);
  return Object.freeze({
    read(timeoutMs = 0) {
      if (bufferedLines.length !== 0) {
        return Promise.resolve(bufferedLines.shift());
      }
      if (failure !== null) return Promise.reject(failure);
      return new Promise((resolve, reject) => {
        const reader = { reject, resolve, timer: null };
        if (timeoutMs > 0) {
          reader.timer = setTimeout(() => {
            const index = readers.indexOf(reader);
            if (index !== -1) readers.splice(index, 1);
            reject(daemonError("DAEMON_TIMEOUT", "daemon request timed out"));
          }, timeoutMs);
          reader.timer.unref?.();
        }
        readers.push(reader);
      });
    },
    stop() {
      if (stopped) return;
      stopped = true;
      socket.removeListener("close", onClose);
      socket.removeListener("error", onError);
      fail(daemonError("DAEMON_TRANSPORT", "daemon transport closed"));
    },
  });
}

export function createCandidateProducerCancellationAdapter(options) {
  let captured;
  try {
    captured = captureOwnData(
      options,
      new Set(["workerRuntime", "headManager", "resolveHeadJobId"]),
    );
  } catch {
    throw new TypeError("invalid candidate producer cancellation adapter options");
  }
  if (
    captured.size !== 3 ||
    typeof captured.get("workerRuntime")?.abortCancelled !== "function" ||
    typeof captured.get("headManager")?.cancel !== "function" ||
    typeof captured.get("resolveHeadJobId") !== "function"
  ) {
    throw new TypeError("invalid candidate producer cancellation adapter options");
  }
  const workerRuntime = captured.get("workerRuntime");
  const headManager = captured.get("headManager");
  const resolveHeadJobId = captured.get("resolveHeadJobId");

  return async function onCandidateProducerCancelled(context) {
    let cancellation;
    try {
      cancellation = captureOwnData(
        context,
        new Set(["kind", "originId", "projectId", "publicJobId", "replayed"]),
      );
    } catch {
      throw new TypeError("invalid candidate producer cancellation context");
    }
    const kind = cancellation.get("kind");
    const originId = cancellation.get("originId");
    const projectId = cancellation.get("projectId");
    const publicJobId = cancellation.get("publicJobId");
    const replayed = cancellation.get("replayed");
    const publicIdPattern =
      kind === "WORKER" ? /^DS-[0-9a-f]{32}$/ : /^SH-[0-9a-f]{32}$/;
    if (
      cancellation.size !== 5 ||
      !["WORKER", "HEAD"].includes(kind) ||
      !isPositiveSafeInteger(originId) ||
      requireDaemonProjectId(projectId) !== projectId ||
      typeof publicJobId !== "string" ||
      !publicIdPattern.test(publicJobId) ||
      typeof replayed !== "boolean"
    ) {
      throw new TypeError("invalid candidate producer cancellation context");
    }
    if (replayed) {
      return Object.freeze({
        kind,
        public_job_id: publicJobId,
        producer_job_id: null,
        aborted: false,
        replayed: true,
      });
    }
    const frozenContext = Object.freeze({
      kind,
      originId,
      projectId,
      publicJobId,
      replayed: false,
    });
    if (kind === "WORKER") {
      const aborted = await Reflect.apply(
        workerRuntime.abortCancelled,
        workerRuntime,
        [frozenContext],
      );
      if (!Array.isArray(aborted)) {
        throw daemonError(
          "PRODUCER_CANCEL_FAILED",
          "candidate worker cancellation adapter returned an invalid receipt",
        );
      }
      return Object.freeze({
        kind,
        public_job_id: publicJobId,
        producer_job_id: null,
        aborted: aborted.length > 0,
        replayed: false,
      });
    }
    const producerJobId = await Reflect.apply(
      resolveHeadJobId,
      undefined,
      [frozenContext],
    );
    if (
      typeof producerJobId !== "string" ||
      !/^SH-[A-Za-z0-9-]+$/.test(producerJobId)
    ) {
      throw daemonError(
        "PRODUCER_CANCEL_FAILED",
        "candidate head cancellation did not resolve an exact active producer",
      );
    }
    const receipt = await Reflect.apply(
      headManager.cancel,
      headManager,
      [producerJobId],
    );
    let capturedReceipt;
    try {
      capturedReceipt = captureOwnData(
        receipt,
        new Set(["job_id", "cancelled", "reason"]),
      );
    } catch {
      throw daemonError(
        "PRODUCER_CANCEL_FAILED",
        "candidate head cancellation returned an invalid receipt",
      );
    }
    if (
      capturedReceipt.size !== 3 ||
      capturedReceipt.get("job_id") !== producerJobId ||
      capturedReceipt.get("cancelled") !== true ||
      typeof capturedReceipt.get("reason") !== "string"
    ) {
      throw daemonError(
        "PRODUCER_CANCEL_FAILED",
        "candidate head producer was not active at committed cancellation",
      );
    }
    return Object.freeze({
      kind,
      public_job_id: publicJobId,
      producer_job_id: producerJobId,
      aborted: true,
      replayed: false,
    });
  };
}

function captureCandidateV2RpcHandlers(value) {
  if (value === undefined) return Object.freeze({});
  const allowed = new Set([
    "batchSubmit",
    "headPlan",
    "prepareHeadPlan",
    "headSubmit",
    "prepareHeadSubmit",
    "health",
    "workerSubmit",
  ]);
  const captured = captureOwnData(value, allowed);
  const handlers = {};
  for (const [name, handler] of captured) {
    if (typeof handler !== "function") {
      throw new TypeError("invalid candidate v2 RPC handlers");
    }
    handlers[name] = handler;
  }
  return Object.freeze(handlers);
}

function captureCandidateV2DaemonOptions(options) {
  const captured = captureOwnData(
    options,
    new Set([
      "projectId",
      "store",
      "secret",
      "capabilityVerifier",
      "legacyValidators",
      "rpcHandlers",
      "cancelWhenUnobserved",
      "onProducerCancelled",
      "migrationAttestation",
      "handshakeTimeoutMs",
      "requestTimeoutMs",
      "maxConnections",
    ]),
  );
  for (const key of [
    "projectId",
    "store",
    "secret",
    "capabilityVerifier",
    "legacyValidators",
  ]) {
    if (!captured.has(key)) {
      throw new TypeError("invalid candidate v2 daemon options");
    }
  }
  const projectId = requireDaemonProjectId(captured.get("projectId"));
  const store = captured.get("store");
  const secret = requireDaemonSecret(captured.get("secret"));
  const capabilityVerifier = captured.get("capabilityVerifier");
  if (
    store === null ||
    typeof store !== "object" ||
    typeof capabilityVerifier !== "function"
  ) {
    throw new TypeError("invalid candidate v2 daemon options");
  }
  const schemaVersion = Reflect.apply(
    candidateDependencyMethod(store, "getCandidateStoreSchemaVersion"),
    store,
    [],
  );
  if (schemaVersion !== CANDIDATE_DAEMON_PROFILE.storeSchema) {
    throw daemonError("PROTOCOL_MISMATCH", "candidate store schema mismatch");
  }
  if (
    !captured.has("migrationAttestation") ||
    typeof store.verifyCandidateMigrationAttestation !== "function"
  ) {
    throw daemonError(
      "MIGRATION_UNATTESTED",
      "candidate store migration is unattested",
    );
  }
  const migrationAttestation = Reflect.apply(
    store.verifyCandidateMigrationAttestation,
    store,
    [captured.get("migrationAttestation")],
  );
  if (
    migrationAttestation?.attested !== true ||
    migrationAttestation.projectId !== projectId
  ) {
    throw daemonError(
      "MIGRATION_UNATTESTED",
      "candidate store migration is unattested",
    );
  }
  const cancelWhenUnobserved = captured.has("cancelWhenUnobserved")
    ? captured.get("cancelWhenUnobserved")
    : false;
  const onProducerCancelled = captured.has("onProducerCancelled")
    ? captured.get("onProducerCancelled")
    : undefined;
  const handshakeTimeoutMs = captured.has("handshakeTimeoutMs")
    ? captured.get("handshakeTimeoutMs")
    : 5000;
  const requestTimeoutMs = captured.has("requestTimeoutMs")
    ? captured.get("requestTimeoutMs")
    : 30_000;
  const maxConnections = captured.has("maxConnections")
    ? captured.get("maxConnections")
    : 16;
  if (
    typeof cancelWhenUnobserved !== "boolean" ||
    (onProducerCancelled !== undefined &&
      typeof onProducerCancelled !== "function") ||
    !Number.isSafeInteger(handshakeTimeoutMs) ||
    handshakeTimeoutMs < 1 ||
    handshakeTimeoutMs > MAX_TIMER_DELAY_MS ||
    !Number.isSafeInteger(requestTimeoutMs) ||
    requestTimeoutMs < 1 ||
    requestTimeoutMs > MAX_TIMER_DELAY_MS ||
    !Number.isSafeInteger(maxConnections) ||
    maxConnections < 1 ||
    maxConnections > 128
  ) {
    throw new TypeError("invalid candidate v2 daemon options");
  }
  return Object.freeze({
    projectId,
    store,
    secret,
    capabilityVerifier,
    legacyValidators: captured.get("legacyValidators"),
    rpcHandlers: captureCandidateV2RpcHandlers(captured.get("rpcHandlers")),
    migrationAttestation,
    cancelWhenUnobserved,
    onProducerCancelled,
    handshakeTimeoutMs,
    requestTimeoutMs,
    maxConnections,
  });
}

function defaultCandidateV2Health(api, session, migrationAttestation) {
  const metrics = api.metrics();
  const spent = metrics.spent_nano_usd;
  const reserved = metrics.reserved_nano_usd;
  const total = spent + reserved;
  const ceiling =
    Number.isSafeInteger(total) && total < Number.MAX_SAFE_INTEGER
      ? Math.max(total + 1, 1)
      : Number.MAX_SAFE_INTEGER;
  const queued = metrics.queued_jobs;
  const capacityPolicy = resolveCapacityPolicy();
  const readLimit = capacityPolicy.pools["deepluna-read"].capacity;
  const hardReasons = [
    ...(CANDIDATE_DAEMON_RUNTIME_ACCEPTED ? [] : ["activation-disabled"]),
    ...(CANDIDATE_DAEMON_PROFILE.activation.productionActivationEligible
      ? []
      : ["production-ineligible"]),
    ...(CANDIDATE_DAEMON_PROFILE.activation.windowsAcl === "PROVEN"
      ? []
      : ["windows-acl-unproven"]),
  ];
  const softReasons = queued > 0 ? ["capacity-pressure"] : [];
  const reasonCodes = [...hardReasons, ...softReasons];
  const readiness =
    hardReasons.length > 0
      ? "BLOCKED"
      : softReasons.length > 0
        ? "DEGRADED"
        : "READY";
  return Object.freeze({
    schema_version: 1,
    readiness,
    reason_codes: Object.freeze(reasonCodes),
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
      read_limit: readLimit,
      write_limit: 1,
      active_reads: 0,
      active_writes: 0,
      queued,
    }),
    migration: Object.freeze({
      attested: migrationAttestation.attested,
      attestation_id: migrationAttestation.attestationId,
      source_set_hash: migrationAttestation.sourceSetHash,
      unresolved_collisions: migrationAttestation.unresolvedCollisions,
      operational_imports: migrationAttestation.operationalImports,
    }),
    budget: Object.freeze({
      spent_nano_usd: spent,
      open_reserved_nano_usd: reserved,
      next_call_estimate_nano_usd: 1,
      project_ceiling_nano_usd: ceiling,
      unknown_reservations: metrics.unknown_transmissions,
    }),
    circuits: Object.freeze({
      provider_calls_enabled: readiness === "READY",
      unavailable_pools: 0,
    }),
  });
}

function dispatchCandidateV2Rpc({
  api,
  handlers,
  migrationAttestation,
  method,
  payload,
  prepared,
  session,
}) {
  const custom = (name) => {
    const handler = handlers[name];
    if (handler === undefined) {
      throw daemonError("ACTIVATION_DISABLED", "candidate operation is inactive");
    }
    return Reflect.apply(handler, undefined, [
      Object.freeze({
        api,
        method,
        payload,
        ...(prepared === undefined ? {} : { prepared }),
        session,
      }),
    ]);
  };
  switch (method) {
    case "health":
      return handlers.health === undefined
        ? defaultCandidateV2Health(api, session, migrationAttestation)
        : custom("health");
    case "worker.submit":
      return custom("workerSubmit");
    case "job.status":
      return api.status({ jobId: payload.jobId });
    case "job.cancel":
      return api.cancel({ jobId: payload.jobId });
    case "metrics":
      return api.metrics();
    case "batch.submit":
      return custom("batchSubmit");
    case "batch.status":
      return api.batchStatus({ batchId: payload.batchId });
    case "batch.metrics":
      return api.batchMetrics();
    case "head.plan":
      return custom("headPlan");
    case "head.submit":
      return custom("headSubmit");
    case "head.status":
      return api.headStatus({ jobId: payload.jobId });
    case "head.cancel":
      return api.headCancel({ jobId: payload.jobId });
    case "head.metrics":
      return api.headMetrics();
    default:
      throw daemonError("UNKNOWN_METHOD", "unknown candidate RPC method");
  }
}

export function createCandidateOrchestratorDaemonV2(options) {
  const config = captureCandidateV2DaemonOptions(options);
  const address = candidateDaemonPipeNameForProject(config.projectId);
  const executeProtocolRequest = candidateDependencyMethod(
    config.store,
    "executeCandidateProtocolRequest",
  );
  const sockets = new Set();
  const connections = new Set();
  let server = null;
  let lifecycle = "NEW";
  let aclEvidence = null;
  let acceptingConnections = false;

  const detachSession = (subscriptions, detachApi) => {
    for (const jobId of subscriptions.workers) {
      try {
        detachApi.detach({ jobId });
      } catch {
        // A terminal or already-detached claim needs no transport cleanup.
      }
    }
    for (const jobId of subscriptions.heads) {
      try {
        detachApi.headCancel({ jobId });
      } catch {
        // Head detach is also idempotent at the session boundary.
      }
    }
    subscriptions.workers.clear();
    subscriptions.heads.clear();
  };

  const serve = async (socket) => {
    sockets.add(socket);
    const channel = createCandidateV2LineChannel(socket);
    const subscriptions = { workers: new Set(), heads: new Set() };
    let detachApi = null;
    try {
      const clientHello = parseCandidateV2Frame(
        await channel.read(config.handshakeTimeoutMs),
        CANDIDATE_DAEMON_WIRE_LIMITS.maxHandshakeBytes,
      );
      const session = await establishCandidateOriginSession({
        secret: config.secret,
        clientHello,
        store: config.store,
        capabilityVerifier: config.capabilityVerifier,
        serverNonce: crypto.randomBytes(32).toString("hex"),
        serverInstanceId: CANDIDATE_PROCESS_BOOT_ID,
      });
      await writeRawLine(
        socket,
        canonicalCandidateDaemonJson(session.serverHello),
        config.handshakeTimeoutMs,
      );
      const transcriptHash = candidateHandshakeTranscriptHash(
        clientHello,
        session.serverHello,
      );
      const clientFinish = parseCandidateV2Frame(
        await channel.read(config.handshakeTimeoutMs),
        CANDIDATE_DAEMON_WIRE_LIMITS.maxHandshakeBytes,
      );
      if (!verifyCandidateClientFinish(config.secret, transcriptHash, clientFinish)) {
        throw daemonError("AUTH_FAILED", "authentication failed");
      }
      await writeRawLine(
        socket,
        canonicalCandidateDaemonJson(
          createCandidateServerFinish(config.secret, transcriptHash),
        ),
        config.handshakeTimeoutMs,
      );
      const api = createCandidateOriginBoundApi({
        session,
        store: config.store,
        cancelWhenUnobserved: config.cancelWhenUnobserved,
      });
      detachApi = createCandidateOriginBoundApi({
        session,
        store: config.store,
        cancelWhenUnobserved: false,
      });
      let lastSequence = -1;
      while (!socket.destroyed) {
        const frame = parseCandidateV2Frame(
          await channel.read(),
          CANDIDATE_DAEMON_WIRE_LIMITS.maxFrameBytes,
        );
        validateCandidateRpcRequestEnvelope(frame, config.legacyValidators);
        if (frame.seq <= lastSequence) {
          throw daemonError("INVALID_REQUEST", "request sequence is stale");
        }
        lastSequence = frame.seq;
        const prepareHandler = frame.type === "head.plan"
          ? config.rpcHandlers.prepareHeadPlan
          : frame.type === "head.submit"
            ? config.rpcHandlers.prepareHeadSubmit
            : undefined;
        let prepared;
        let preparationError = null;
        if (prepareHandler !== undefined) {
          try {
            prepared = await Reflect.apply(prepareHandler, undefined, [
              Object.freeze({
                method: frame.type,
                payload: frame.payload,
                session,
              }),
            ]);
            if (prepared === undefined) {
              throw daemonError(
                "CAPABILITY_MISMATCH",
                "candidate head preflight returned no durable input",
              );
            }
          } catch (error) {
            preparationError = candidateV2PublicError(error);
          }
        }
        let durable;
        try {
          durable = Reflect.apply(executeProtocolRequest, config.store, [{
            originId: session.originId,
            projectId: session.projectId,
            requestId: frame.requestId,
            method: frame.type,
            payload: frame.payload,
            execute: () => {
              if (preparationError !== null) {
                return { ok: false, error: preparationError };
              }
              try {
                const result = dispatchCandidateV2Rpc({
                  api,
                  handlers: config.rpcHandlers,
                  migrationAttestation: config.migrationAttestation,
                  method: frame.type,
                  payload: frame.payload,
                  prepared,
                  session,
                });
                if (result?.then instanceof Function) {
                  throw daemonError(
                    "CAPABILITY_MISMATCH",
                    "candidate durable commit handler must be synchronous",
                  );
                }
                return {
                  ok: true,
                  result,
                };
              } catch (error) {
                return { ok: false, error: candidateV2PublicError(error) };
              }
            },
          }]);
        } catch (error) {
          durable = {
            replayed: false,
            outcome: { ok: false, error: candidateV2PublicError(error) },
          };
        }
        const response = {
          seq: frame.seq,
          requestId: frame.requestId,
          ...durable.outcome,
        };
        validateCandidateRpcResponseEnvelope(
          frame.type,
          response,
          frame.type === "health"
            ? {
                projectId: session.projectId,
                originId: session.originId,
                profile: CANDIDATE_DAEMON_PROFILE,
                runtimeBuildHash: session.serverHello.runtimeBuildHash,
                serverInstanceId: session.serverHello.serverInstanceId,
                serverStartedAtMs: session.serverHello.serverStartedAtMs,
              }
            : undefined,
        );
        if (
          response.ok === true &&
          response.result.producer_cancelled === true &&
          config.onProducerCancelled !== undefined &&
          (frame.type === "job.cancel" || frame.type === "head.cancel")
        ) {
          await Reflect.apply(config.onProducerCancelled, undefined, [
            Object.freeze({
              kind: frame.type === "job.cancel" ? "WORKER" : "HEAD",
              originId: session.originId,
              projectId: session.projectId,
              publicJobId: response.result.job_id,
              replayed: durable.replayed,
            }),
          ]);
        }
        if (response.ok === true) {
          if (frame.type === "worker.submit") {
            subscriptions.workers.add(response.result.job_id);
          } else if (frame.type === "head.submit") {
            subscriptions.heads.add(response.result.job_id);
          } else if (
            frame.type === "job.cancel" &&
            response.result.detached === true
          ) {
            subscriptions.workers.delete(response.result.job_id);
          } else if (
            frame.type === "head.cancel" &&
            response.result.detached === true
          ) {
            subscriptions.heads.delete(response.result.job_id);
          }
        }
        await writeRawLine(
          socket,
          canonicalCandidateDaemonJson(response),
          config.requestTimeoutMs,
        );
      }
    } catch {
      // Pre-auth and malformed transports close without disclosing server state.
    } finally {
      if (detachApi !== null) detachSession(subscriptions, detachApi);
      channel.stop();
      sockets.delete(socket);
      closeCandidateV2Socket(socket);
    }
  };

  return Object.freeze({
    address,
    async start() {
      if (lifecycle === "RUNNING") {
        return Object.freeze({
          status: "STARTED",
          windows_acl: aclEvidence.windows_acl,
        });
      }
      if (lifecycle !== "NEW") {
        throw daemonError("DAEMON_STATE", "candidate daemon cannot restart");
      }
      lifecycle = "STARTING";
      server = net.createServer((socket) => {
        if (!acceptingConnections) {
          closeCandidateV2Socket(socket);
          return;
        }
        if (sockets.size >= config.maxConnections) {
          closeCandidateV2Socket(socket);
          return;
        }
        const connection = serve(socket).finally(() => connections.delete(connection));
        connections.add(connection);
      });
      await new Promise((resolve, reject) => {
        const onError = (error) => {
          server.removeListener("listening", onListening);
          reject(error);
        };
        const onListening = () => {
          server.removeListener("error", onError);
          resolve();
        };
        server.once("error", onError);
        server.once("listening", onListening);
        server.listen({
          path: address,
          readableAll: false,
          writableAll: false,
        });
      });
      try {
        aclEvidence = attestCandidateWindowsNamedPipeAcl(address);
      } catch (error) {
        const current = server;
        server = null;
        if (current !== null) {
          await new Promise((resolve) => {
            try {
              current.close(() => resolve());
            } catch {
              resolve();
            }
          });
        }
        lifecycle = "STOPPED";
        throw error;
      }
      await new Promise((resolve) => setImmediate(resolve));
      acceptingConnections = true;
      lifecycle = "RUNNING";
      return Object.freeze({
        status: "STARTED",
        windows_acl: aclEvidence.windows_acl,
      });
    },
    async stop() {
      if (lifecycle === "STOPPED") return;
      lifecycle = "STOPPING";
      acceptingConnections = false;
      for (const socket of [...sockets]) closeCandidateV2Socket(socket);
      if (server !== null) {
        const current = server;
        server = null;
        await new Promise((resolve) => {
          try {
            current.close(() => resolve());
          } catch {
            resolve();
          }
        });
      }
      await Promise.allSettled([...connections]);
      lifecycle = "STOPPED";
    },
  });
}

function captureCandidateV2ClientOptions(options) {
  const captured = captureOwnData(
    options,
    new Set([
      "projectId",
      "secret",
      "originThreadHash",
      "originCapabilityHash",
      "legacyValidators",
      "timeoutMs",
    ]),
  );
  for (const key of [
    "projectId",
    "secret",
    "originThreadHash",
    "originCapabilityHash",
    "legacyValidators",
  ]) {
    if (!captured.has(key)) {
      throw new TypeError("invalid candidate v2 client options");
    }
  }
  const timeoutMs = captured.has("timeoutMs") ? captured.get("timeoutMs") : 5000;
  if (
    !Number.isSafeInteger(timeoutMs) ||
    timeoutMs < 1 ||
    timeoutMs > MAX_TIMER_DELAY_MS
  ) {
    throw new TypeError("invalid candidate v2 client options");
  }
  return Object.freeze({
    projectId: requireDaemonProjectId(captured.get("projectId")),
    secret: requireDaemonSecret(captured.get("secret")),
    originThreadHash: captured.get("originThreadHash"),
    originCapabilityHash: captured.get("originCapabilityHash"),
    legacyValidators: captured.get("legacyValidators"),
    timeoutMs,
  });
}

export async function connectCandidateDaemonClientV2(options) {
  const config = captureCandidateV2ClientOptions(options);
  const address = candidateDaemonPipeNameForProject(config.projectId);
  const socket = net.createConnection(address);
  await new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.removeListener("connect", onConnect);
      socket.removeListener("error", onError);
      if (error === undefined) resolve();
      else reject(error);
    };
    const onConnect = () => finish();
    const onError = () =>
      finish(daemonError("DAEMON_TRANSPORT", "daemon transport failed"));
    const timer = setTimeout(
      () => finish(daemonError("DAEMON_TIMEOUT", "daemon request timed out")),
      config.timeoutMs,
    );
    timer.unref?.();
    socket.once("connect", onConnect);
    socket.once("error", onError);
  });
  const channel = createCandidateV2LineChannel(socket);
  const clientHello = createCandidateClientHello(config.secret, {
    protocol: CANDIDATE_DAEMON_PROFILE.protocol,
    rpcSchema: CANDIDATE_DAEMON_PROFILE.rpcSchema,
    projectId: config.projectId,
    originThreadHash: config.originThreadHash,
    originCapabilityHash: config.originCapabilityHash,
    clientRelease: CANDIDATE_DAEMON_RELEASE,
    runtimeBuildHash: CANDIDATE_RUNTIME_BUILD_HASH,
    clientNonce: crypto.randomBytes(32).toString("hex"),
    requiredCapabilities: CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
  });
  try {
    await writeRawLine(
      socket,
      canonicalCandidateDaemonJson(clientHello),
      config.timeoutMs,
    );
    const serverHello = parseCandidateV2Frame(
      await channel.read(config.timeoutMs),
      CANDIDATE_DAEMON_WIRE_LIMITS.maxHandshakeBytes,
    );
    if (!verifyCandidateServerHello(config.secret, clientHello, serverHello)) {
      throw daemonError("AUTH_FAILED", "authentication failed");
    }
    const transcriptHash = candidateHandshakeTranscriptHash(
      clientHello,
      serverHello,
    );
    await writeRawLine(
      socket,
      canonicalCandidateDaemonJson(
        createCandidateClientFinish(config.secret, transcriptHash),
      ),
      config.timeoutMs,
    );
    const serverFinish = parseCandidateV2Frame(
      await channel.read(config.timeoutMs),
      CANDIDATE_DAEMON_WIRE_LIMITS.maxHandshakeBytes,
    );
    if (!verifyCandidateServerFinish(config.secret, transcriptHash, serverFinish)) {
      throw daemonError("AUTH_FAILED", "authentication failed");
    }
    let sequence = 0;
    let requestChain = Promise.resolve();
    let closed = false;
    const client = {
      address,
      originId: serverHello.originId,
      runtimeBuildHash: serverHello.runtimeBuildHash,
      serverInstanceId: serverHello.serverInstanceId,
      serverStartedAtMs: serverHello.serverStartedAtMs,
      request(method, payload, requestOptions = {}) {
        const operation = requestChain.then(async () => {
          if (closed || socket.destroyed) {
            throw daemonError("DAEMON_TRANSPORT", "daemon transport closed");
          }
          const captured = captureOwnData(
            requestOptions,
            new Set(["requestId"]),
          );
          const requestId = captured.has("requestId")
            ? captured.get("requestId")
            : `RQ-${crypto.randomBytes(16).toString("hex")}`;
          sequence += 1;
          const frame = { seq: sequence, requestId, type: method, payload };
          validateCandidateRpcRequestEnvelope(frame, config.legacyValidators);
          await writeRawLine(
            socket,
            canonicalCandidateDaemonJson(frame),
            config.timeoutMs,
          );
          const response = parseCandidateV2Frame(
            await channel.read(config.timeoutMs),
            CANDIDATE_DAEMON_WIRE_LIMITS.maxFrameBytes,
          );
          validateCandidateRpcResponseEnvelope(
            method,
            response,
            method === "health"
              ? {
                  projectId: config.projectId,
                  originId: serverHello.originId,
                  profile: CANDIDATE_DAEMON_PROFILE,
                  runtimeBuildHash: serverHello.runtimeBuildHash,
                  serverInstanceId: serverHello.serverInstanceId,
                  serverStartedAtMs: serverHello.serverStartedAtMs,
                }
              : undefined,
          );
          if (
            response.seq !== frame.seq ||
            response.requestId !== frame.requestId
          ) {
            throw daemonError("PROTOCOL_MISMATCH", "response identity mismatch");
          }
          if (response.ok !== true) {
            throw daemonError(response.error.code, response.error.message);
          }
          return response.result;
        });
        requestChain = operation.catch(() => undefined);
        return operation;
      },
      close() {
        if (closed) return;
        closed = true;
        channel.stop();
        closeCandidateV2Socket(socket);
      },
    };
    return Object.freeze(client);
  } catch (error) {
    channel.stop();
    closeCandidateV2Socket(socket);
    throw error;
  }
}

function requireDaemonProjectId(value) {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    value.length > MAX_DAEMON_PROJECT_ID ||
    value.trim() !== value ||
    !/^[A-Za-z0-9._:-]+$/.test(value)
  ) {
    throw new TypeError("invalid project identity");
  }
  return value;
}

function requireDaemonIdentifier(value, maximumLength, message) {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    value.length > maximumLength ||
    value.trim() !== value ||
    value.includes("\0")
  ) {
    throw new TypeError(message);
  }
  return value;
}

function requireDaemonSecret(value) {
  if (!Buffer.isBuffer(value) || value.length < 32) {
    throw new TypeError("secret must be a Buffer of at least 32 bytes");
  }
  return Buffer.from(value);
}

function canonicalDaemonJson(root) {
  const ancestors = new Set();
  let nodes = 0;

  function serialize(value, depth) {
    nodes += 1;
    if (nodes > 10_000 || depth > 64) throw new TypeError();
    if (value === null) return "null";
    if (typeof value === "string" || typeof value === "boolean") {
      return JSON.stringify(value);
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) throw new TypeError();
      return JSON.stringify(value);
    }
    if (typeof value !== "object" || ancestors.has(value)) throw new TypeError();
    if (Object.getOwnPropertySymbols(value).length !== 0) throw new TypeError();
    ancestors.add(value);
    try {
      if (Array.isArray(value)) {
        const descriptors = Object.getOwnPropertyDescriptors(value);
        const length = descriptors.length?.value;
        if (!Number.isSafeInteger(length) || length < 0) throw new TypeError();
        const keys = Reflect.ownKeys(descriptors).filter((key) => key !== "length");
        if (
          keys.length !== length ||
          keys.some((key, index) => key !== String(index))
        ) {
          throw new TypeError();
        }
        return `[${keys
          .map((key) => {
            const descriptor = descriptors[key];
            if (!descriptor.enumerable || !Object.hasOwn(descriptor, "value")) {
              throw new TypeError();
            }
            return serialize(descriptor.value, depth + 1);
          })
          .join(",")}]`;
      }
      const prototype = Object.getPrototypeOf(value);
      if (prototype !== Object.prototype && prototype !== null) throw new TypeError();
      const descriptors = Object.getOwnPropertyDescriptors(value);
      const keys = Reflect.ownKeys(descriptors);
      if (keys.some((key) => typeof key !== "string")) throw new TypeError();
      return `{${keys
        .sort()
        .map((key) => {
          const descriptor = descriptors[key];
          if (!descriptor.enumerable || !Object.hasOwn(descriptor, "value")) {
            throw new TypeError();
          }
          return `${JSON.stringify(key)}:${serialize(descriptor.value, depth + 1)}`;
        })
        .join(",")}}`;
    } finally {
      ancestors.delete(value);
    }
  }

  try {
    return serialize(root, 0);
  } catch {
    throw new TypeError("value must be strict plain JSON data");
  }
}

function strictObject(value, allowedKeys, requiredKeys = allowedKeys) {
  const captured = captureOwnData(value, allowedKeys);
  if (
    captured.size !== requiredKeys.size ||
    [...requiredKeys].some((key) => !captured.has(key))
  ) {
    throw new TypeError("invalid frame");
  }
  return captured;
}

function parseStrictFrame(line) {
  let parsed;
  try {
    parsed = JSON.parse(line);
    canonicalDaemonJson(parsed);
  } catch {
    throw new TypeError("invalid frame");
  }
  return parsed;
}

function hmacHex(secret, value) {
  return crypto.createHmac("sha256", secret).update(JSON.stringify(value)).digest("hex");
}

function constantTimeMacMatches(expectedHex, candidate) {
  const valid = typeof candidate === "string" && /^[0-9a-f]{64}$/.test(candidate);
  const candidateBytes = valid ? Buffer.from(candidate, "hex") : Buffer.alloc(32);
  const expectedBytes = Buffer.from(expectedHex, "hex");
  const matches = crypto.timingSafeEqual(expectedBytes, candidateBytes);
  return valid && matches;
}

function attachBoundedFrameReader(socket, onFrame, onViolation) {
  let buffered = Buffer.alloc(0);
  const queue = [];
  let processing = false;
  let stopped = false;
  const processQueue = async () => {
    if (processing || stopped) return;
    processing = true;
    socket.pause();
    try {
      while (queue.length !== 0 && !stopped) {
        await onFrame(queue.shift());
      }
    } catch {
      onViolation();
    } finally {
      processing = false;
      if (!stopped && !socket.destroyed) socket.resume();
    }
  };
  const handleData = (chunk) => {
    if (stopped || !Buffer.isBuffer(chunk)) {
      onViolation();
      return;
    }
    buffered = Buffer.concat([buffered, chunk], buffered.length + chunk.length);
    while (true) {
      const newline = buffered.indexOf(0x0a);
      if (newline === -1) {
        if (buffered.length > MAX_DAEMON_FRAME_BYTES) onViolation();
        break;
      }
      if (newline === 0 || newline > MAX_DAEMON_FRAME_BYTES) {
        onViolation();
        return;
      }
      const line = buffered.subarray(0, newline).toString("utf8");
      buffered = Buffer.from(buffered.subarray(newline + 1));
      queue.push(line);
      if (queue.length > 16) {
        onViolation();
        return;
      }
    }
    void processQueue();
  };
  socket.on("data", handleData);
  return () => {
    stopped = true;
    socket.removeListener("data", handleData);
    queue.length = 0;
    buffered = Buffer.alloc(0);
  };
}

function writeRawLine(socket, line, timeoutMs = DEFAULT_DAEMON_TIMEOUT_MS) {
  if (
    typeof line !== "string" ||
    Buffer.byteLength(line, "utf8") > MAX_DAEMON_FRAME_BYTES ||
    socket.destroyed
  ) {
    return Promise.reject(daemonError("DAEMON_TRANSPORT", "daemon transport unavailable"));
  }
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.removeListener("error", onError);
      socket.removeListener("close", onClose);
      socket.removeListener("drain", onDrain);
      if (error === undefined) resolve();
      else reject(error);
    };
    const onError = () => finish(daemonError("DAEMON_TRANSPORT", "daemon transport failed"));
    const onClose = () => finish(daemonError("DAEMON_TRANSPORT", "daemon transport closed"));
    const onDrain = () => finish();
    const timer = setTimeout(
      () => finish(daemonError("DAEMON_TIMEOUT", "daemon write timeout")),
      timeoutMs,
    );
    timer.unref?.();
    socket.once("error", onError);
    socket.once("close", onClose);
    let writable;
    try {
      writable = socket.write(`${line}\n`);
    } catch {
      finish(daemonError("DAEMON_TRANSPORT", "daemon transport failed"));
      return;
    }
    if (writable) finish();
    else socket.once("drain", onDrain);
  });
}

function readBoundedLine(socket, timeoutMs) {
  return new Promise((resolve, reject) => {
    let buffered = Buffer.alloc(0);
    let settled = false;
    const finish = (error, line) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.removeListener("data", onData);
      socket.removeListener("error", onError);
      socket.removeListener("close", onClose);
      if (error === undefined) resolve(line);
      else reject(error);
    };
    const onData = (chunk) => {
      if (
        !Buffer.isBuffer(chunk) ||
        buffered.length + chunk.length > MAX_DAEMON_FRAME_BYTES + 1
      ) {
        finish(daemonError("DAEMON_PROTOCOL", "invalid daemon frame"));
        return;
      }
      buffered = Buffer.concat([buffered, chunk], buffered.length + chunk.length);
      const newline = buffered.indexOf(0x0a);
      if (newline === -1) return;
      if (newline === 0 || newline > MAX_DAEMON_FRAME_BYTES) {
        finish(daemonError("DAEMON_PROTOCOL", "invalid daemon frame"));
        return;
      }
      finish(undefined, buffered.subarray(0, newline).toString("utf8"));
    };
    const onError = () => finish(daemonError("DAEMON_TRANSPORT", "daemon transport failed"));
    const onClose = () => finish(daemonError("DAEMON_TRANSPORT", "daemon transport closed"));
    const timer = setTimeout(
      () => finish(daemonError("DAEMON_TIMEOUT", "daemon handshake timeout")),
      timeoutMs,
    );
    timer.unref?.();
    socket.on("data", onData);
    socket.once("error", onError);
    socket.once("close", onClose);
  });
}

export function pipeNameForProject(projectId) {
  const exactProjectId = requireDaemonProjectId(projectId);
  const digest = crypto
    .createHash("sha256")
    .update(exactProjectId)
    .digest("hex")
    .slice(0, 20);
  return `\\\\.\\pipe\\codex-deepluna-${digest}-v${DAEMON_PROTOCOL_VERSION}`;
}

export function getCandidateActivationPreflightReceipt(options) {
  const captured = captureOwnData(
    options,
    new Set([
      "filename",
      "projectId",
      "expectedDaemonPid",
      "expectedProcessBootId",
      "expectedRuntimeBuildHash",
      "authenticatedDaemonIdentity",
      "now",
      "pipeOwnerResolver",
    ]),
  );
  const filename = captured.get("filename");
  const projectId = requireDaemonProjectId(captured.get("projectId"));
  const expectedDaemonPid = captured.get("expectedDaemonPid");
  const expectedProcessBootId = captured.get("expectedProcessBootId");
  const expectedRuntimeBuildHash = captured.get("expectedRuntimeBuildHash");
  const now = captured.has("now") ? captured.get("now") : Date.now;
  const pipeOwnerResolver = captured.has("pipeOwnerResolver")
    ? captured.get("pipeOwnerResolver")
    : getCandidateWindowsNamedPipeServerProcessId;
  if (
    typeof filename !== "string" ||
    filename.trim() === "" ||
    !path.isAbsolute(filename) ||
    filename.includes("\0") ||
    !isWindowsPid(expectedDaemonPid) ||
    typeof expectedProcessBootId !== "string" ||
    !/^DI-[0-9a-f]{32}$/.test(expectedProcessBootId) ||
    typeof expectedRuntimeBuildHash !== "string" ||
    !/^[0-9a-f]{64}$/.test(expectedRuntimeBuildHash) ||
    typeof now !== "function" ||
    typeof pipeOwnerResolver !== "function"
  ) {
    throw new TypeError("invalid activation preflight request");
  }
  let authenticatedDaemonIdentity = null;
  if (captured.has("authenticatedDaemonIdentity")) {
    const identity = captureOwnData(
      captured.get("authenticatedDaemonIdentity"),
      new Set([
        "projectId",
        "processId",
        "processBootId",
        "runtimeBuildHash",
        "serverRelease",
      ]),
    );
    const identityProjectId = requireDaemonProjectId(identity.get("projectId"));
    const processId = identity.get("processId");
    const processBootId = identity.get("processBootId");
    const runtimeBuildHash = identity.get("runtimeBuildHash");
    const serverRelease = identity.get("serverRelease");
    if (
      !isWindowsPid(processId) ||
      typeof processBootId !== "string" ||
      !/^DI-[0-9a-f]{32}$/.test(processBootId) ||
      typeof runtimeBuildHash !== "string" ||
      !/^[0-9a-f]{64}$/.test(runtimeBuildHash) ||
      typeof serverRelease !== "string" ||
      !/^[0-9]+\.[0-9]+\.[0-9]+$/.test(serverRelease)
    ) {
      throw new TypeError("invalid authenticated daemon identity");
    }
    authenticatedDaemonIdentity = Object.freeze({
      projectId: identityProjectId,
      processId,
      processBootId,
      runtimeBuildHash,
      serverRelease,
    });
  }

  const address = candidateDaemonPipeNameForProject(projectId);
  const store = readCandidateActivationQuiescenceSnapshot({
    filename,
    projectId,
    now,
  });
  let pipe = Object.freeze({
    address,
    serverProcessId: null,
    status: "UNAVAILABLE",
  });
  try {
    const evidence = pipeOwnerResolver(address);
    const processIds = Object.getOwnPropertyDescriptor(
      evidence,
      "processIds",
    );
    if (
      processIds?.enumerable === true &&
      Object.hasOwn(processIds, "value") &&
      Array.isArray(processIds.value) &&
      processIds.value.length !== 1
    ) {
      throw new TypeError("ambiguous named-pipe ownership");
    }
    const exact = captureOwnData(
      evidence,
      new Set(["address", "processId", "status"]),
    );
    if (
      exact.get("address") !== address ||
      !isWindowsPid(exact.get("processId")) ||
      exact.get("status") !== "PROVEN"
    ) {
      throw new TypeError("ambiguous named-pipe ownership");
    }
    pipe = Object.freeze({
      address,
      serverProcessId: exact.get("processId"),
      status: "PROVEN",
    });
  } catch (error) {
    if (
      error instanceof TypeError &&
      error.message === "ambiguous named-pipe ownership"
    ) {
      pipe = Object.freeze({
        address,
        serverProcessId: null,
        status: "AMBIGUOUS",
      });
    }
  }
  const daemon =
    authenticatedDaemonIdentity === null
      ? Object.freeze({
          authenticated: false,
          projectId: null,
          processId: null,
          processBootId: null,
          runtimeBuildHash: null,
          serverRelease: null,
        })
      : Object.freeze({
          authenticated: true,
          ...authenticatedDaemonIdentity,
        });
  const reasons = [...store.reasons];
  if (!store.readOnlyUnchanged) reasons.push("STORE_CHANGED_DURING_PREFLIGHT");
  if (pipe.status === "UNAVAILABLE") reasons.push("PIPE_OWNER_UNAVAILABLE");
  if (pipe.status === "AMBIGUOUS") reasons.push("PIPE_OWNER_AMBIGUOUS");
  if (
    pipe.status === "PROVEN" &&
    pipe.serverProcessId !== expectedDaemonPid
  ) {
    reasons.push("PIPE_OWNER_PID_MISMATCH");
  }
  if (authenticatedDaemonIdentity === null) {
    reasons.push("AUTHENTICATED_DAEMON_IDENTITY_UNAVAILABLE");
  } else {
    if (authenticatedDaemonIdentity.projectId !== projectId) {
      reasons.push("AUTHENTICATED_PROJECT_MISMATCH");
    }
    if (authenticatedDaemonIdentity.processId !== expectedDaemonPid) {
      reasons.push("AUTHENTICATED_PID_MISMATCH");
    }
    if (
      pipe.status === "PROVEN" &&
      authenticatedDaemonIdentity.processId !== pipe.serverProcessId
    ) {
      reasons.push("AUTHENTICATED_PIPE_PID_MISMATCH");
    }
    if (
      authenticatedDaemonIdentity.processBootId !== expectedProcessBootId
    ) {
      reasons.push("AUTHENTICATED_BOOT_MISMATCH");
    }
    if (
      authenticatedDaemonIdentity.runtimeBuildHash !== expectedRuntimeBuildHash
    ) {
      reasons.push("AUTHENTICATED_BUILD_MISMATCH");
    }
    if (
      authenticatedDaemonIdentity.serverRelease !== CANDIDATE_DAEMON_RELEASE
    ) {
      reasons.push("AUTHENTICATED_RELEASE_MISMATCH");
    }
  }
  const frozenReasons = Object.freeze([...new Set(reasons)]);
  const sourceRuntime = Object.freeze({
    serverRelease: CANDIDATE_DAEMON_RELEASE,
    runtimeBuildHash: CANDIDATE_RUNTIME_BUILD_HASH,
  });
  const precondition = Object.freeze({
    schemaVersion: 1,
    projectId,
    expectedDaemonPid,
    expectedProcessBootId,
    expectedRuntimeBuildHash,
    sourceRuntime,
    storePreconditionHash: store.preconditionHash,
    storeIdentityHash: store.storeIdentityHash,
    storeReadOnlyUnchanged: store.readOnlyUnchanged,
    pipe,
    daemon,
    reasons: frozenReasons,
  });
  return Object.freeze({
    ...precondition,
    capturedAtMs: store.capturedAtMs,
    store,
    quiescent: store.quiescent && frozenReasons.length === 0,
    preconditionHash: crypto
      .createHash("sha256")
      .update(
        `deepluna-activation-preflight-v1\0${canonicalCandidateDaemonJson(
          precondition,
        )}`,
      )
      .digest("hex"),
  });
}

function captureRunners(value) {
  if (value === undefined) return Object.freeze({});
  const captured = captureOwnData(value, new Set(Object.keys(value)));
  const runners = {};
  for (const [key, runner] of captured) {
    if (!/^[a-z][a-z0-9_-]{0,63}$/.test(key) || typeof runner !== "function") {
      throw new TypeError("invalid daemon runners");
    }
    runners[key] = runner;
  }
  return Object.freeze(runners);
}

function captureDaemonOptions(options) {
  const captured = captureOwnData(
    options,
    new Set([
      "projectId",
      "stateRoot",
      "secret",
      "runners",
      "capacityPolicy",
      "providerPoolPolicy",
      "writerAdmission",
      "dispatchIntervalMs",
      "leaseMs",
      "handshakeTimeoutMs",
      "requestTimeoutMs",
      "now",
      "fingerprintInputs",
      "protocolVersion",
      "maxConnections",
    ]),
  );
  const projectId = requireDaemonProjectId(captured.get("projectId"));
  const stateRoot = captured.get("stateRoot");
  if (
    typeof stateRoot !== "string" ||
    !path.isAbsolute(stateRoot) ||
    stateRoot.includes("\0")
  ) {
    throw new TypeError("stateRoot must be an absolute path");
  }
  const secret = requireDaemonSecret(captured.get("secret"));
  const runners = captureRunners(captured.get("runners"));
  const capacityPolicy = captured.has("capacityPolicy")
    ? captured.get("capacityPolicy")
    : resolveCapacityPolicy();
  const providerPoolPolicy = captured.has("providerPoolPolicy")
    ? captured.get("providerPoolPolicy")
    : DEFAULT_PROVIDER_POOL_POLICY;
  const writerAdmission = captured.has("writerAdmission")
    ? captured.get("writerAdmission")
    : () => false;
  const dispatchIntervalMs = captured.has("dispatchIntervalMs")
    ? captured.get("dispatchIntervalMs")
    : DEFAULT_DISPATCH_INTERVAL_MS;
  const leaseMs = captured.has("leaseMs")
    ? captured.get("leaseMs")
    : DEFAULT_LEASE_MS;
  const handshakeTimeoutMs = captured.has("handshakeTimeoutMs")
    ? captured.get("handshakeTimeoutMs")
    : DEFAULT_DAEMON_TIMEOUT_MS;
  const requestTimeoutMs = captured.has("requestTimeoutMs")
    ? captured.get("requestTimeoutMs")
    : DEFAULT_DAEMON_TIMEOUT_MS;
  const now = captured.has("now") ? captured.get("now") : Date.now;
  const fingerprintInputs = captured.has("fingerprintInputs")
    ? captured.get("fingerprintInputs")
    : async ({ generation }) => generation.inputFingerprint;
  const protocolVersion = captured.has("protocolVersion")
    ? captured.get("protocolVersion")
    : DAEMON_PROTOCOL_VERSION;
  const maxConnections = captured.has("maxConnections")
    ? captured.get("maxConnections")
    : DEFAULT_MAX_DAEMON_CONNECTIONS;
  for (const value of [
    dispatchIntervalMs,
    leaseMs,
    handshakeTimeoutMs,
    requestTimeoutMs,
  ]) {
    if (!Number.isSafeInteger(value) || value < 1 || value > MAX_TIMER_DELAY_MS) {
      throw new TypeError("invalid daemon timeout");
    }
  }
  if (
    typeof now !== "function" ||
    typeof fingerprintInputs !== "function" ||
    typeof writerAdmission !== "function" ||
    !Number.isSafeInteger(protocolVersion) ||
    protocolVersion < 1 ||
    !Number.isSafeInteger(maxConnections) ||
    maxConnections < 1 ||
    maxConnections > 1024
  ) {
    throw new TypeError("invalid daemon options");
  }
  return {
    projectId,
    stateRoot: path.resolve(stateRoot),
    secret,
    runners,
    capacityPolicy,
    providerPoolPolicy,
    writerAdmission,
    dispatchIntervalMs,
    leaseMs,
    handshakeTimeoutMs,
    requestTimeoutMs,
    now,
    fingerprintInputs,
    protocolVersion,
    maxConnections,
  };
}

function publicProtocolError(error) {
  const allowed = new Set([
    "IDEMPOTENCY_CONFLICT",
    "INVALID_CANCEL_STATE",
    "STALE_GENERATION",
    "JOB_NOT_FOUND",
    "UNKNOWN_REQUEST",
    "QUEUE_LIMIT",
    "ACTIVE_TASK_LIMIT",
    "UNKNOWN_POOL",
    "DIAGNOSTIC_ONLY",
    "INVALID_ROLE",
    "WRITER_ADMISSION_DENIED",
  ]);
  const code = allowed.has(error?.code) ? error.code : "INVALID_REQUEST";
  const messages = {
    IDEMPOTENCY_CONFLICT: "request conflicts with durable identity",
    INVALID_CANCEL_STATE: "generation cannot be canceled",
    STALE_GENERATION: "generation is stale",
    JOB_NOT_FOUND: "job not found",
    UNKNOWN_REQUEST: "unknown request type",
    QUEUE_LIMIT: "queue limit reached",
    ACTIVE_TASK_LIMIT: "active task limit reached",
    UNKNOWN_POOL: "unknown pool",
    DIAGNOSTIC_ONLY: "diagnostic-only pool",
    INVALID_ROLE: "worker role is not admitted",
    WRITER_ADMISSION_DENIED: "writer admission is disabled",
    INVALID_REQUEST: "request rejected",
  };
  return { code, message: messages[code] };
}

function envelopeDurableResponse(responseJson, sequence, requestId) {
  const logical = parseStrictFrame(responseJson);
  if (logical?.ok === true) {
    const fields = strictObject(logical, new Set(["ok", "result"]));
    canonicalDaemonJson(fields.get("result"));
    return canonicalDaemonJson({
      seq: sequence,
      requestId,
      ok: true,
      result: fields.get("result"),
    });
  }
  const fields = strictObject(logical, new Set(["ok", "error"]));
  if (fields.get("ok") !== false) throw new TypeError("invalid durable response");
  const errorFields = strictObject(
    fields.get("error"),
    new Set(["code", "message"]),
  );
  requireDaemonIdentifier(
    errorFields.get("code"),
    128,
    "invalid durable response",
  );
  requireDaemonIdentifier(
    errorFields.get("message"),
    256,
    "invalid durable response",
  );
  return canonicalDaemonJson({
    seq: sequence,
    requestId,
    ok: false,
    error: {
      code: errorFields.get("code"),
      message: errorFields.get("message"),
    },
  });
}

function captureRequestPayload(type, payload, projectId, store, admitGeneration) {
  if (type === "health") {
    strictObject(payload, new Set(), new Set());
    return {
      result: {
        protocol: DAEMON_PROTOCOL_VERSION,
        projectId,
        activationStatus: ACTIVATION_STATUS,
      },
    };
  }
  if (type === "submit") {
    const captured = strictObject(payload, new Set(["contract"]));
    const contract = captured.get("contract");
    canonicalDaemonJson(contract);
    if (contract?.projectId !== projectId) {
      throw daemonError("INVALID_REQUEST", "request rejected");
    }
    const result = store.enqueue(contract);
    if (result.state === "QUEUED") admitGeneration(result);
    return { result, action: "SUBMIT" };
  }
  if (type === "cancel") {
    const captured = strictObject(
      payload,
      new Set(["jobId", "generation", "actor", "reason"]),
    );
    const result = store.cancelGeneration({
      jobId: captured.get("jobId"),
      generation: captured.get("generation"),
      actor: captured.get("actor"),
      reason: captured.get("reason"),
    });
    return { result, action: "CANCEL" };
  }
  if (type === "status") {
    const captured = strictObject(payload, new Set(["jobId", "generation"]));
    const result = store.getGeneration(
      captured.get("jobId"),
      captured.get("generation"),
    );
    if (result === null) throw daemonError("JOB_NOT_FOUND", "job not found");
    return { result };
  }
  if (type === "subscribe") {
    const captured = strictObject(
      payload,
      new Set(["jobId", "afterSequence"]),
    );
    return {
      result: store.listEvents(
        captured.get("jobId"),
        captured.get("afterSequence"),
      ),
    };
  }
  throw daemonError("UNKNOWN_REQUEST", "unknown request type");
}

function preflightRequestAdmission(
  type,
  payload,
  projectId,
  writerAdmission,
  validateCircuitPoolId,
) {
  if (type !== "submit") return;
  const captured = strictObject(payload, new Set(["contract"]));
  const contract = captured.get("contract");
  canonicalDaemonJson(contract);
  if (contract?.projectId !== projectId) {
    throw daemonError("INVALID_REQUEST", "request rejected");
  }
  let laneId;
  try {
    laneId = capacityLaneForRole(contract.role);
  } catch {
    throw daemonError("INVALID_ROLE", "worker role is not admitted");
  }
  validateCircuitPoolId(contract.poolId);
  if (laneId !== "deepluna-write") return;
  if (!writerAdmissionAllows(contract, writerAdmission)) {
    throw daemonError(
      "WRITER_ADMISSION_DENIED",
      "writer admission is disabled",
    );
  }
}

function writerAdmissionAllows(contract, writerAdmission) {
  let admitted = false;
  try {
    admitted = writerAdmission(Object.freeze({ ...contract })) === true;
  } catch {
    admitted = false;
  }
  return admitted;
}

export function createOrchestratorDaemon(options) {
  const config = captureDaemonOptions(options);
  const address = pipeNameForProject(config.projectId);
  const sockets = new Set();
  const runningPromises = new Set();
  const generationByJobId = new Map();
  const inertGenerationByJobId = new Map();
  const activeByJobId = new Map();
  let store = null;
  let scheduler = new WeightedFairScheduler(config.capacityPolicy);
  let pools = new ProviderPoolRegistry(config.providerPoolPolicy, {
    now: config.now,
  });
  let server = null;
  let dispatchTimer = null;
  let lifecycle = "NEW";
  let accepting = false;
  let tickActive = false;
  let tickPromise = null;
  let startPromise = null;
  let stopPromise = null;
  let acceptCompletions = false;

  const exactGenerationIsInert = (generation) =>
    inertGenerationByJobId.get(generation.jobId) === generation.generation;

  const dispatchGeneration = (generation) => {
    if (generation?.payload !== undefined || store === null) return generation;
    return (
      store.getDispatchGeneration(generation.jobId, generation.generation) ??
      generation
    );
  };

  const generationPassesWriterGate = (generation) =>
    generation.role !== "WRITER" ||
    writerAdmissionAllows(generation, config.writerAdmission);

  const markGenerationInert = (generation) => {
    scheduler.remove(generation.jobId);
    scheduler.release(generation.jobId);
    generationByJobId.delete(generation.jobId);
    inertGenerationByJobId.set(generation.jobId, generation.generation);
  };

  const enqueueSchedulerGeneration = (generation) => {
    const exactGeneration = dispatchGeneration(generation);
    if (exactGenerationIsInert(exactGeneration)) return false;
    if (!generationPassesWriterGate(exactGeneration)) {
      markGenerationInert(exactGeneration);
      return false;
    }
    inertGenerationByJobId.delete(exactGeneration.jobId);
    try {
      scheduler.enqueue({
        jobId: exactGeneration.jobId,
        taskId: exactGeneration.taskId,
        poolId: capacityLaneForRole(exactGeneration.role),
        priority: exactGeneration.priority,
        createdAtMs: exactGeneration.createdAtMs,
        role: exactGeneration.role,
      });
      generationByJobId.set(
        exactGeneration.jobId,
        exactGeneration.generation,
      );
      return true;
    } catch (error) {
      if (error?.code !== "DUPLICATE_JOB") throw error;
      generationByJobId.set(
        exactGeneration.jobId,
        exactGeneration.generation,
      );
      return false;
    }
  };

  const releaseResources = (job, circuitPoolId, identity = undefined) => {
    const active = activeByJobId.get(job.jobId);
    if (
      identity !== undefined &&
      (active === undefined ||
        active.identity.attemptId !== identity.attemptId ||
        active.identity.epoch !== identity.epoch)
    ) {
      return false;
    }
    if (active !== undefined) {
      clearInterval(active.heartbeatTimer);
      activeByJobId.delete(job.jobId);
    }
    pools.recordOutcome(circuitPoolId, {
      class: "CANCELLATION",
      jobId: job.jobId,
    });
    pools.release(circuitPoolId, job.jobId);
    scheduler.release(job.jobId);
    generationByJobId.delete(job.jobId);
    return true;
  };

  const completeRun = async (job, generation, identity, runner) => {
    try {
      let runnerResult;
      try {
        runnerResult = await runner(
          Object.freeze({
            job: Object.freeze({ ...job }),
            generation: Object.freeze({ ...generation }),
            contract: generation.payload,
            lease: Object.freeze({ ...identity }),
          }),
        );
        const resultFields = strictObject(
          runnerResult,
          new Set(["resultHash"]),
        );
        requireDaemonIdentifier(
          resultFields.get("resultHash"),
          256,
          "invalid runner result",
        );
        if (!acceptCompletions || store === null) return;
        const currentFingerprint = await config.fingerprintInputs({
          job: Object.freeze({ ...job }),
          generation: Object.freeze({ ...generation }),
          contract: generation.payload,
        });
        requireDaemonIdentifier(
          currentFingerprint,
          256,
          "invalid input fingerprint",
        );
        if (!acceptCompletions || store === null) return;
        if (!store.beginValidation(identity)) return;
        const acceptance = store.acceptResult({
          ...identity,
          resultHash: resultFields.get("resultHash"),
          inputFingerprint: currentFingerprint,
        });
        pools.recordOutcome(generation.poolId, {
          class: acceptance.accepted ? "SUCCESS" : "SCHEMA_FAILURE",
          jobId: job.jobId,
        });
      } catch {
        if (acceptCompletions && store !== null) {
          try {
            store.quarantineAttempt({
              ...identity,
              failureClass: "RUNNER_OR_SCHEMA_FAILURE",
            });
            pools.recordOutcome(generation.poolId, {
              class: "SCHEMA_FAILURE",
              jobId: job.jobId,
            });
          } catch {
            // A cancellation, stale epoch, or concurrent stop already fenced this attempt.
          }
        }
      }
    } finally {
      releaseResources(job, generation.poolId, identity);
      if (accepting) queueMicrotask(() => void tick().catch(() => {}));
    }
  };

  const runTick = async () => {
    if (!accepting || store === null || tickActive) return;
    tickActive = true;
    try {
      const recovered = store.recoverExpiredLeases();
      for (const recovery of recovered) {
        const active = activeByJobId.get(recovery.jobId);
        if (active !== undefined) {
          releaseResources(
            active.job,
            active.circuitPoolId,
            active.identity,
          );
        }
        if (recovery.action === "REQUEUED") {
          const generation = store.getDispatchGeneration(
            recovery.jobId,
            recovery.generation,
          );
          if (
            generation !== null &&
            !exactGenerationIsInert(generation)
          ) {
            enqueueSchedulerGeneration(generation);
          }
        }
      }
      for (const queued of store.listQueuedGenerations()) {
        if (
          !generationByJobId.has(queued.jobId) &&
          !exactGenerationIsInert(queued)
        ) {
          enqueueSchedulerGeneration(queued);
        }
      }
      for (const laneId of Object.keys(scheduler.snapshot().pools)) {
        while (accepting) {
          const laneSnapshot = scheduler.snapshot().pools[laneId];
          const deniedWriters = [];
          const job = scheduler.dispatchNextEligible(
            laneId,
            (candidate) => {
              const generationNumber = generationByJobId.get(candidate.jobId);
              const generation =
                generationNumber === undefined
                  ? null
                  : store.getDispatchGeneration(
                      candidate.jobId,
                      generationNumber,
                    );
              if (generation === null) return false;
              if (!generationPassesWriterGate(generation)) {
                deniedWriters.push(generation);
                return false;
              }
              if (
                typeof config.runners[generation.role.toLowerCase()] !==
                "function"
              ) {
                return false;
              }
              return pools.canDispatch(generation.poolId).allowed;
            },
            { scanLimit: Math.max(1, laneSnapshot.queued) },
          );
          for (const generation of deniedWriters) {
            markGenerationInert(generation);
          }
          if (job === null) break;
          const generationNumber = generationByJobId.get(job.jobId);
          const generation =
            generationNumber === undefined
              ? null
              : store.getDispatchGeneration(job.jobId, generationNumber);
          const runner =
            generation === null
              ? undefined
              : config.runners[generation.role.toLowerCase()];
          if (generation === null || typeof runner !== "function") {
            scheduler.release(job.jobId);
            if (generation !== null) enqueueSchedulerGeneration(generation);
            break;
          }
          const acquired = pools.tryAcquire(generation.poolId, job.jobId);
          if (!acquired.acquired) {
            scheduler.release(job.jobId);
            enqueueSchedulerGeneration(generation);
            break;
          }
          let identity;
          try {
            identity = store.leaseGeneration({
              jobId: job.jobId,
              generation: generation.generation,
              workerId: `daemon-${process.pid}`,
              leaseMs: config.leaseMs,
            });
          } catch (error) {
            releaseResources(job, generation.poolId);
            throw error;
          }
          if (identity === null) {
            releaseResources(job, generation.poolId);
            continue;
          }
          if (!generationPassesWriterGate(generation)) {
            try {
              store.cancelGeneration({
                jobId: generation.jobId,
                generation: generation.generation,
                actor: "daemon-writer-admission",
                reason: "writer admission denied before runner",
              });
            } finally {
              releaseResources(job, generation.poolId);
              inertGenerationByJobId.delete(generation.jobId);
            }
            continue;
          }
          const heartbeatTimer = setInterval(() => {
            if (!acceptCompletions || store === null) return;
            try {
              store.heartbeat({ ...identity, leaseMs: config.leaseMs });
            } catch {
              // The synchronized tick will recover or fence the exact lease.
            }
          }, Math.max(1, Math.floor(config.leaseMs / 3)));
          heartbeatTimer.unref();
          activeByJobId.set(job.jobId, {
            job,
            circuitPoolId: generation.poolId,
            identity,
            heartbeatTimer,
          });
          const running = completeRun(job, generation, identity, runner);
          runningPromises.add(running);
          running.finally(() => runningPromises.delete(running));
        }
      }
    } finally {
      tickActive = false;
    }
  };

  const tick = () => {
    if (tickPromise !== null) return tickPromise;
    tickPromise = runTick().finally(() => {
      tickPromise = null;
    });
    return tickPromise;
  };

  const closeSocket = (socket) => {
    if (!socket.destroyed) socket.destroy();
  };

  const postCommitAction = (action, result) => {
    if (action === "SUBMIT" && result.state === "QUEUED") {
      void tick().catch(() => {});
    } else if (action === "CANCEL") {
      const active = activeByJobId.get(result.jobId);
      if (active !== undefined) {
        releaseResources(
          active.job,
          active.circuitPoolId,
          active.identity,
        );
      } else {
        scheduler.remove(result.jobId);
        scheduler.release(result.jobId);
        pools.release(result.poolId, result.jobId);
        generationByJobId.delete(result.jobId);
        inertGenerationByJobId.delete(result.jobId);
      }
    }
  };

  const handleConnection = (socket) => {
    if (sockets.size >= config.maxConnections) {
      socket.destroy();
      return;
    }
    sockets.add(socket);
    socket.on("error", () => {});
    socket.once("close", () => sockets.delete(socket));
    let handshakePhase = "HELLO";
    let sessionHello = null;
    let expectedSequence = 1;
    const handshakeTimer = setTimeout(
      () => closeSocket(socket),
      config.handshakeTimeoutMs,
    );
    handshakeTimer.unref?.();
    socket.once("close", () => clearTimeout(handshakeTimer));
    const removeReader = attachBoundedFrameReader(
      socket,
      async (line) => {
        if (handshakePhase !== "AUTHENTICATED") {
          let frame;
          try {
            frame = parseStrictFrame(line);
            if (handshakePhase === "FINISH") {
              const finish = strictObject(frame, new Set(["clientFinishMac"]));
              const expectedFinishMac = hmacHex(config.secret, {
                ...sessionHello,
                phase: "CLIENT_FINISH",
              });
              if (
                !constantTimeMacMatches(
                  expectedFinishMac,
                  finish.get("clientFinishMac"),
                )
              ) {
                throw new TypeError();
              }
              handshakePhase = "AUTHENTICATED";
              clearTimeout(handshakeTimer);
              const finishMac = hmacHex(config.secret, {
                ...sessionHello,
                phase: "SERVER_FINISH",
              });
              await writeRawLine(
                socket,
                canonicalDaemonJson({
                  ok: true,
                  authenticated: true,
                  mac: finishMac,
                }),
                config.requestTimeoutMs,
              );
              return;
            }
            const fields = strictObject(
              frame,
              new Set(["protocol", "projectId", "clientNonce", "mac"]),
            );
            const protocol = fields.get("protocol");
            const projectId = requireDaemonProjectId(fields.get("projectId"));
            const clientNonce = fields.get("clientNonce");
            if (
              !Number.isSafeInteger(protocol) ||
              typeof clientNonce !== "string" ||
              !/^[0-9a-f]{64}$/.test(clientNonce)
            ) {
              throw new TypeError();
            }
            const expectedMac = hmacHex(config.secret, {
              protocol,
              projectId,
              clientNonce,
            });
            if (!constantTimeMacMatches(expectedMac, fields.get("mac"))) {
              throw new TypeError();
            }
            if (projectId !== config.projectId) throw new TypeError();
            const serverNonce = crypto.randomBytes(32).toString("hex");
            if (protocol !== config.protocolVersion) {
              const mismatchMac = hmacHex(config.secret, {
                protocol,
                projectId,
                clientNonce,
                serverNonce,
                error: "PROTOCOL_MISMATCH",
              });
              await writeRawLine(
                socket,
                canonicalDaemonJson({
                  ok: false,
                  serverNonce,
                  mac: mismatchMac,
                  error: {
                    code: "PROTOCOL_MISMATCH",
                    message: "protocol mismatch",
                  },
                }),
                config.requestTimeoutMs,
              );
              closeSocket(socket);
              return;
            }
            const mac = hmacHex(config.secret, {
              protocol,
              projectId,
              clientNonce,
              serverNonce,
            });
            sessionHello = {
              protocol,
              projectId,
              clientNonce,
              serverNonce,
            };
            handshakePhase = "FINISH";
            await writeRawLine(
              socket,
              canonicalDaemonJson({ ok: true, serverNonce, mac }),
              config.requestTimeoutMs,
            );
          } catch {
            closeSocket(socket);
          }
          return;
        }

        let requestId;
        let sequence;
        let fingerprint;
        let rollbackAdmission;
        let requestFrameAccepted = false;
        try {
          if (!accepting || store === null) throw new TypeError();
          const frame = parseStrictFrame(line);
          const fields = strictObject(
            frame,
            new Set(["seq", "requestId", "type", "payload"]),
          );
          sequence = fields.get("seq");
          requestId = requireDaemonIdentifier(
            fields.get("requestId"),
            MAX_DAEMON_REQUEST_ID,
            "invalid request id",
          );
          const type = requireDaemonIdentifier(
            fields.get("type"),
            MAX_DAEMON_TYPE,
            "invalid request type",
          );
          const payload = fields.get("payload");
          canonicalDaemonJson(payload);
          if (!Number.isSafeInteger(sequence) || sequence !== expectedSequence) {
            await writeRawLine(
              socket,
              canonicalDaemonJson({
                ok: false,
                error: {
                  code: "INVALID_SEQUENCE",
                  message: "invalid request sequence",
                },
              }),
              config.requestTimeoutMs,
            );
            closeSocket(socket);
            return;
          }
          expectedSequence += 1;
          requestFrameAccepted = true;
          preflightRequestAdmission(
            type,
            payload,
            config.projectId,
            config.writerAdmission,
            (poolId) => pools.validatePoolId(poolId),
          );
          fingerprint = crypto
            .createHash("sha256")
            .update(canonicalDaemonJson({ type, payload }))
            .digest("hex");
          let postCommit;
          const durable = store.executeProtocolRequest({
            requestId,
            requestFingerprint: fingerprint,
            execute: () => {
              const handled = captureRequestPayload(
                type,
                payload,
                config.projectId,
                store,
                (generation) => {
                  const admitted = enqueueSchedulerGeneration(generation);
                  if (admitted) {
                    rollbackAdmission = () => {
                      scheduler.remove(generation.jobId);
                      generationByJobId.delete(generation.jobId);
                    };
                  }
                },
              );
              postCommit = handled;
              return canonicalDaemonJson({
                ok: true,
                result: handled.result,
              });
            },
          });
          rollbackAdmission = undefined;
          if (!durable.replayed && postCommit !== undefined) {
            postCommitAction(postCommit.action, postCommit.result);
          }
          await writeRawLine(
            socket,
            envelopeDurableResponse(
              durable.responseJson,
              sequence,
              requestId,
            ),
            config.requestTimeoutMs,
          );
        } catch (error) {
          rollbackAdmission?.();
          if (
            error?.code === "DAEMON_TRANSPORT" ||
            error?.code === "DAEMON_TIMEOUT"
          ) {
            closeSocket(socket);
            return;
          }
          const conflict = error?.code === "REQUEST_ID_CONFLICT";
          const responseSequence = Number.isSafeInteger(sequence) ? sequence : 0;
          const responseRequestId =
            typeof requestId === "string" && requestId.length <= MAX_DAEMON_REQUEST_ID
              ? requestId
              : "";
          let logicalResponse = {
            ok: false,
            error: conflict
              ? {
                  code: "REQUEST_ID_CONFLICT",
                  message: "request id conflicts with prior request",
                }
              : publicProtocolError(error),
          };
          let logicalResponseJson = canonicalDaemonJson(logicalResponse);
          if (
            !conflict &&
            store !== null &&
            typeof requestId === "string" &&
            typeof fingerprint === "string"
          ) {
            try {
              const durableError = store.executeProtocolRequest({
                requestId,
                requestFingerprint: fingerprint,
                execute: () => logicalResponseJson,
              });
              logicalResponseJson = durableError.responseJson;
            } catch {
              logicalResponse = {
                ok: false,
                error: {
                  code: "INVALID_REQUEST",
                  message: "request rejected",
                },
              };
              logicalResponseJson = canonicalDaemonJson(logicalResponse);
            }
          }
          let responseJson;
          try {
            responseJson = envelopeDurableResponse(
              logicalResponseJson,
              responseSequence,
              responseRequestId,
            );
          } catch {
            responseJson = canonicalDaemonJson({
              seq: responseSequence,
              requestId: responseRequestId,
              ok: false,
              error: {
                code: "INVALID_REQUEST",
                message: "request rejected",
              },
            });
          }
          try {
            await writeRawLine(
              socket,
              responseJson,
              config.requestTimeoutMs,
            );
          } finally {
            if (
              typeof fingerprint !== "string" &&
              !requestFrameAccepted
            ) {
              closeSocket(socket);
            }
          }
        }
      },
      () => {
        clearTimeout(handshakeTimer);
        removeReader();
        closeSocket(socket);
      },
    );
  };

  const bindServer = (candidate) =>
    new Promise((resolve, reject) => {
      const onError = (error) => {
        candidate.removeListener("listening", onListening);
        reject(error);
      };
      const onListening = () => {
        candidate.removeListener("error", onError);
        resolve();
      };
      candidate.once("error", onError);
      candidate.once("listening", onListening);
      candidate.listen({
        path: address,
        readableAll: false,
        writableAll: false,
      });
    });

  const closeServer = async () => {
    for (const socket of [...sockets]) closeSocket(socket);
    if (server === null) return;
    const current = server;
    server = null;
    await new Promise((resolve) => {
      try {
        current.close(() => resolve());
      } catch {
        resolve();
      }
    });
  };

  const startInternal = async () => {
    if (lifecycle === "RUNNING") return { status: "STARTED" };
    if (lifecycle !== "NEW") throw daemonError("DAEMON_STATE", "daemon cannot restart");
    lifecycle = "STARTING";
    scheduler = new WeightedFairScheduler(config.capacityPolicy);
    pools = new ProviderPoolRegistry(config.providerPoolPolicy, {
      now: config.now,
    });
    try {
      server = net.createServer(handleConnection);
      try {
        await bindServer(server);
      } catch (error) {
        if (error?.code !== "EADDRINUSE") throw error;
        const failedCandidate = server;
        server = null;
        try {
          failedCandidate.close();
        } catch {
          // The failed listener never acquired a transport handle.
        }
        let incumbent;
        try {
          incumbent = await connectDaemonClient({
            projectId: config.projectId,
            secret: config.secret,
            address,
            protocol: config.protocolVersion,
            timeoutMs: config.handshakeTimeoutMs,
          });
          incumbent.close();
        } catch {
          throw daemonError(
            "DAEMON_SINGLETON_UNVERIFIED",
            "existing daemon identity could not be verified",
          );
        }
        lifecycle = "STOPPED";
        return { status: "ALREADY_RUNNING" };
      }
      store = openSchedulerStore({
        filename: path.join(config.stateRoot, "scheduler.sqlite3"),
        now: config.now,
      });
      store.recoverExpiredLeases();
      for (const generation of store.listQueuedGenerations()) {
        enqueueSchedulerGeneration(generation);
      }
      accepting = true;
      acceptCompletions = true;
      lifecycle = "RUNNING";
      dispatchTimer = setInterval(
        () => void tick().catch(() => {}),
        config.dispatchIntervalMs,
      );
      dispatchTimer.unref();
      return { status: "STARTED" };
    } catch (error) {
      accepting = false;
      acceptCompletions = false;
      await closeServer();
      if (store !== null) {
        try {
          store.close();
        } catch {
          // Preserve the primary startup failure.
        }
        store = null;
      }
      lifecycle = "STOPPED";
      throw error;
    }
  };

  const start = () => {
    if (lifecycle === "RUNNING") return Promise.resolve({ status: "STARTED" });
    if (startPromise !== null) return startPromise;
    startPromise = startInternal();
    return startPromise;
  };

  const stop = ({ mode } = {}) => {
    if (!["DRAIN", "TEST_FORCE"].includes(mode)) {
      throw new TypeError("invalid daemon stop mode");
    }
    if (stopPromise !== null) return stopPromise;
    if (lifecycle === "STOPPED" || lifecycle === "NEW") {
      lifecycle = "STOPPED";
      return Promise.resolve();
    }
    stopPromise = (async () => {
      if (lifecycle === "STARTING" && startPromise !== null) {
        try {
          await startPromise;
        } catch {
          lifecycle = "STOPPED";
          return;
        }
      }
      lifecycle = "STOPPING";
      accepting = false;
      if (mode === "TEST_FORCE") acceptCompletions = false;
      if (dispatchTimer !== null) {
        clearInterval(dispatchTimer);
        dispatchTimer = null;
      }
      if (tickPromise !== null) {
        try {
          await tickPromise;
        } catch {
          // Exact per-job cleanup already ran before the tick failure propagated.
        }
      }
      await closeServer();
      if (mode === "DRAIN") {
        await Promise.allSettled([...runningPromises]);
      } else {
        runningPromises.clear();
        for (const active of [...activeByJobId.values()]) {
          releaseResources(
            active.job,
            active.circuitPoolId,
            active.identity,
          );
        }
      }
      acceptCompletions = false;
      for (const active of [...activeByJobId.values()]) {
        clearInterval(active.heartbeatTimer);
      }
      activeByJobId.clear();
      if (store !== null) {
        store.close();
        store = null;
      }
      lifecycle = "STOPPED";
    })();
    return stopPromise;
  };

  return Object.freeze({
    start,
    stop,
    tick,
    address,
    get store() {
      return store;
    },
    get scheduler() {
      return scheduler;
    },
    get pools() {
      return pools;
    },
    activationStatus: ACTIVATION_STATUS,
    aclStatus: "UNPROVEN",
    productionActivationEligible: false,
  });
}

function captureClientOptions(options) {
  const captured = captureOwnData(
    options,
    new Set(["projectId", "secret", "address", "protocol", "timeoutMs"]),
  );
  const projectId = requireDaemonProjectId(captured.get("projectId"));
  const secret = requireDaemonSecret(captured.get("secret"));
  const address = captured.has("address")
    ? captured.get("address")
    : pipeNameForProject(projectId);
  const protocol = captured.has("protocol")
    ? captured.get("protocol")
    : DAEMON_PROTOCOL_VERSION;
  const timeoutMs = captured.has("timeoutMs")
    ? captured.get("timeoutMs")
    : DEFAULT_DAEMON_TIMEOUT_MS;
  if (
    typeof address !== "string" ||
    address.length < 1 ||
    address.length > 512 ||
    !Number.isSafeInteger(protocol) ||
    protocol < 1 ||
    !Number.isSafeInteger(timeoutMs) ||
    timeoutMs < 1 ||
    timeoutMs > MAX_TIMER_DELAY_MS
  ) {
    throw new TypeError("invalid daemon client options");
  }
  return { projectId, secret, address, protocol, timeoutMs };
}

export async function connectDaemonClient(options) {
  const config = captureClientOptions(options);
  const socket = net.createConnection(config.address);
  socket.on("error", () => {});
  await new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(daemonError("DAEMON_TIMEOUT", "daemon connection timeout")),
      config.timeoutMs,
    );
    timer.unref?.();
    socket.once("connect", () => {
      clearTimeout(timer);
      resolve();
    });
    socket.once("error", () => {
      clearTimeout(timer);
      reject(daemonError("DAEMON_TRANSPORT", "daemon connection failed"));
    });
  }).catch((error) => {
    socket.destroy();
    throw error;
  });

  const clientNonce = crypto.randomBytes(32).toString("hex");
  const mac = hmacHex(config.secret, {
    protocol: config.protocol,
    projectId: config.projectId,
    clientNonce,
  });
  try {
    await writeRawLine(
      socket,
      canonicalDaemonJson({
        protocol: config.protocol,
        projectId: config.projectId,
        clientNonce,
        mac,
      }),
      config.timeoutMs,
    );
  } catch (error) {
    socket.destroy();
    throw error;
  }
  let hello;
  try {
    hello = parseStrictFrame(await readBoundedLine(socket, config.timeoutMs));
  } catch (error) {
    socket.destroy();
    if (error?.code === "DAEMON_TIMEOUT") throw error;
    throw daemonError("DAEMON_AUTH_FAILED", "daemon authentication failed");
  }
  let serverNonce;
  try {
    if (hello?.ok === false) {
      const mismatch = strictObject(
        hello,
        new Set(["ok", "serverNonce", "mac", "error"]),
      );
      const mismatchError = strictObject(
        mismatch.get("error"),
        new Set(["code", "message"]),
      );
      const mismatchNonce = mismatch.get("serverNonce");
      const expectedMismatchMac = hmacHex(config.secret, {
        protocol: config.protocol,
        projectId: config.projectId,
        clientNonce,
        serverNonce: mismatchNonce,
        error: "PROTOCOL_MISMATCH",
      });
      if (
        mismatch.get("ok") !== false ||
        mismatchError.get("code") !== "PROTOCOL_MISMATCH" ||
        mismatchError.get("message") !== "protocol mismatch" ||
        typeof mismatchNonce !== "string" ||
        !/^[0-9a-f]{64}$/.test(mismatchNonce) ||
        !constantTimeMacMatches(expectedMismatchMac, mismatch.get("mac"))
      ) {
        throw new TypeError();
      }
      throw daemonError("PROTOCOL_MISMATCH", "protocol mismatch");
    }
    const fields = strictObject(
      hello,
      new Set(["ok", "serverNonce", "mac"]),
    );
    serverNonce = fields.get("serverNonce");
    if (
      fields.get("ok") !== true ||
      typeof serverNonce !== "string" ||
      !/^[0-9a-f]{64}$/.test(serverNonce)
    ) {
      throw new TypeError();
    }
    const expectedMac = hmacHex(config.secret, {
      protocol: config.protocol,
      projectId: config.projectId,
      clientNonce,
      serverNonce,
    });
    if (!constantTimeMacMatches(expectedMac, fields.get("mac"))) throw new TypeError();
  } catch (error) {
    socket.destroy();
    if (error?.code === "PROTOCOL_MISMATCH") throw error;
    throw daemonError("DAEMON_AUTH_FAILED", "daemon authentication failed");
  }
  const sessionHello = {
    protocol: config.protocol,
    projectId: config.projectId,
    clientNonce,
    serverNonce,
  };
  try {
    await writeRawLine(
      socket,
      canonicalDaemonJson({
        clientFinishMac: hmacHex(config.secret, {
          ...sessionHello,
          phase: "CLIENT_FINISH",
        }),
      }),
      config.timeoutMs,
    );
  } catch (error) {
    socket.destroy();
    throw error;
  }
  let finish;
  try {
    finish = parseStrictFrame(await readBoundedLine(socket, config.timeoutMs));
    const fields = strictObject(
      finish,
      new Set(["ok", "authenticated", "mac"]),
    );
    const expectedFinishMac = hmacHex(config.secret, {
      ...sessionHello,
      phase: "SERVER_FINISH",
    });
    if (
      fields.get("ok") !== true ||
      fields.get("authenticated") !== true ||
      !constantTimeMacMatches(expectedFinishMac, fields.get("mac"))
    ) {
      throw new TypeError();
    }
  } catch (error) {
    socket.destroy();
    if (error?.code === "DAEMON_TIMEOUT") throw error;
    throw daemonError("DAEMON_AUTH_FAILED", "daemon authentication failed");
  }

  let sequence = 0;
  let closed = false;
  const pending = new Map();
  let writeChain = Promise.resolve();
  const removeReader = attachBoundedFrameReader(
    socket,
    async (line) => {
      let response;
      try {
        response = parseStrictFrame(line);
        const envelope = strictObject(
          response,
          response?.ok === true
            ? new Set(["seq", "requestId", "ok", "result"])
            : new Set(["seq", "requestId", "ok", "error"]),
        );
        const requestId = requireDaemonIdentifier(
          envelope.get("requestId"),
          MAX_DAEMON_REQUEST_ID,
          "invalid response request id",
        );
        const entry = pending.get(requestId);
        if (
          entry === undefined ||
          envelope.get("seq") !== entry.sequence ||
          !Number.isSafeInteger(envelope.get("seq"))
        ) {
          throw new TypeError();
        }
        if (envelope.get("ok") === true) {
          canonicalDaemonJson(envelope.get("result"));
        } else {
          if (envelope.get("ok") !== false) throw new TypeError();
          const errorFields = strictObject(
            envelope.get("error"),
            new Set(["code", "message"]),
          );
          requireDaemonIdentifier(
            errorFields.get("code"),
            128,
            "invalid response error",
          );
          requireDaemonIdentifier(
            errorFields.get("message"),
            256,
            "invalid response error",
          );
        }
      } catch {
        socket.destroy();
        return;
      }
      const requestId = response.requestId;
      const entry = pending.get(requestId);
      pending.delete(requestId);
      clearTimeout(entry.timer);
      if (response.ok === true) {
        entry.resolve(response.result);
      } else {
        const error = daemonError(
          typeof response?.error?.code === "string"
            ? response.error.code
            : "DAEMON_PROTOCOL",
          typeof response?.error?.message === "string"
            ? response.error.message
            : "daemon request failed",
        );
        entry.reject(error);
      }
    },
    () => socket.destroy(),
  );
  const detach = () => {
    if (closed) return;
    closed = true;
    removeReader();
    socket.destroy();
    for (const entry of pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(daemonError("DAEMON_DETACHED", "daemon client detached"));
    }
    pending.clear();
  };
  socket.once("close", detach);

  const request = async (type, payload, options = undefined) => {
    if (closed) throw daemonError("DAEMON_DETACHED", "daemon client detached");
    requireDaemonIdentifier(type, MAX_DAEMON_TYPE, "invalid request type");
    canonicalDaemonJson(payload);
    const requestId =
      options === undefined
        ? crypto.randomUUID()
        : requireDaemonIdentifier(
            strictObject(options, new Set(["requestId"])).get("requestId"),
            MAX_DAEMON_REQUEST_ID,
            "invalid request id",
          );
    if (pending.has(requestId)) {
      throw daemonError(
        "DAEMON_REQUEST_PENDING",
        "daemon request id is already pending",
      );
    }
    if (pending.size >= MAX_DAEMON_PENDING_REQUESTS) {
      throw daemonError("DAEMON_BACKPRESSURE", "too many pending daemon requests");
    }
    sequence += 1;
    if (!Number.isSafeInteger(sequence)) {
      throw daemonError("DAEMON_PROTOCOL", "request sequence exhausted");
    }
    const response = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(requestId);
        reject(daemonError("DAEMON_TIMEOUT", "daemon request timeout"));
        detach();
      }, config.timeoutMs);
      timer.unref?.();
      pending.set(requestId, { resolve, reject, timer, sequence });
    });
    try {
      const frame = canonicalDaemonJson({
        seq: sequence,
        requestId,
        type,
        payload,
      });
      const writeOperation = writeChain.then(() =>
        writeRawLine(socket, frame, config.timeoutMs),
      );
      writeChain = writeOperation.catch(() => {});
      await writeOperation;
    } catch (error) {
      const entry = pending.get(requestId);
      if (entry !== undefined) {
        clearTimeout(entry.timer);
        pending.delete(requestId);
        entry.reject(error);
      }
      detach();
    }
    return response;
  };

  return Object.freeze({
    request,
    subscribe(jobId, afterSequence) {
      return request("subscribe", { jobId, afterSequence });
    },
    close: detach,
  });
}
