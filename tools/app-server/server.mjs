// perfume-chem App Server — authed HTTP backend for browser-ChatGPT writes.
// Serves:
//   Option A: local apply inbox  (GET /api/health, POST /api/apply, POST /api/commit)
//   Option D2: Apps SDK UI connectDomains target (same endpoints, CORS-enabled)
//
// Security discipline (mirrors the delegation daemon):
//   - Bearer token auth (APP_SERVER_TOKEN env; compare via timing-safe digest)
//   - All file paths are workspace-relative; absolute paths and .. escapes rejected
//   - Patch apply via `git apply --check` then `git apply`; no shell interpolation
//   - Commit requires explicit message; never force-push
//   - Optional read-only mode (APP_SERVER_READONLY=1)
//   - Symlinks never followed for reads/writes
import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const WORKSPACE = path.resolve(process.env.APP_SERVER_ROOT ?? process.cwd());
const PORT = Number(process.env.APP_SERVER_PORT ?? 4519);
const TOKEN = process.env.APP_SERVER_TOKEN ?? "";
const READONLY = process.env.APP_SERVER_READONLY === "1";
const MAX_BODY = 2_000_000;
const MAX_PATCH = 500_000;

if (!TOKEN) {
  console.error("[app-server] APP_SERVER_TOKEN is required");
  process.exit(1);
}

function safeEqual(a, b) {
  const ha = crypto.createHash("sha256").update(String(a)).digest();
  const hb = crypto.createHash("sha256").update(String(b)).digest();
  return crypto.timingSafeEqual(ha, hb);
}

// Fenced deny-list: paths that must never be read or written through the API,
// even though they live inside the workspace. Mirrors the sidecar proposal's fence.
const DENY_SEGMENTS = [
  ".git", ".env", ".codex", ".ssh", "node_modules", ".venv", "__pycache__",
  "archive", "output/verification", "output/lab-backups",
];
const DENY_PATTERNS = [
  /(^|\/)\.env(\.[a-z0-9]+)?$/i,      // .env, .env.local, .env.production
  /(^|\/)id_rsa$/, /(^|\/)id_ed25519$/, // private keys
  /(^|\/).*\.(pem|key|p12|pfx|jks)$/i,  // key material
  /(^|\/)secrets?\.(json|txt|yaml|yml)$/i,
  /(^|\/)\.secret-bak$/i,
];

function assertNotFenced(rel) {
  const segments = rel.split(/[\\/]+/).filter(Boolean);
  for (const seg of segments) {
    if (DENY_SEGMENTS.includes(seg)) {
      throw new Error(`path is fenced (denied segment: ${seg})`);
    }
  }
  for (const pattern of DENY_PATTERNS) {
    if (pattern.test(rel)) {
      throw new Error("path is fenced (denied pattern)");
    }
  }
}

function workspaceRelative(rel) {
  if (typeof rel !== "string" || rel.length === 0) throw new Error("path required");
  if (path.isAbsolute(rel)) throw new Error("absolute paths not allowed");
  const norm = path.normalize(rel);
  if (norm.startsWith("..") || norm.includes(`..${path.sep}`) || norm === "..") {
    throw new Error("path escapes workspace");
  }
  const full = path.resolve(WORKSPACE, norm);
  if (full !== WORKSPACE && !full.startsWith(WORKSPACE + path.sep)) {
    throw new Error("path escapes workspace");
  }
  assertNotFenced(norm.replace(/\\/g, "/"));
  return { rel: norm, full };
}

function lstatNoFollow(full) {
  try { return fs.lstatSync(full); } catch { return null; }
}

function readFileSafe(full) {
  const st = lstatNoFollow(full);
  if (!st) throw new Error("file does not exist");
  if (st.isSymbolicLink()) throw new Error("symbolic links not allowed");
  if (!st.isFile()) throw new Error("not a regular file");
  const bytes = fs.readFileSync(full);
  return { bytes, sha256: crypto.createHash("sha256").update(bytes).digest("hex") };
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const p = spawn(cmd, args, { cwd: WORKSPACE, windowsHide: true, ...opts });
    let out = "", err = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", (d) => (err += d));
    p.on("close", (code) => resolve({ code, out, err }));
  });
}

async function git(args) {
  const r = await run("git", args);
  return { ok: r.code === 0, code: r.code, out: r.out.trim(), err: r.err.trim() };
}

// Fence-scan a unified diff: every touched file (a/ and b/ headers) must pass the
// deny-list. A patch bypasses the path-parameter API, so it is scanned directly.
function assertPatchNotFenced(patchText) {
  const lines = patchText.split(/\r?\n/);
  for (const line of lines) {
    const m = /^[+-]{3} (?:a|b)\/(.+)$/.exec(line) || /^diff --git a\/(.+) b\//.exec(line);
    if (!m) continue;
    const rel = m[1].replace(/\\/g, "/");
    try {
      assertNotFenced(rel);
    } catch (error) {
      throw new Error(`patch touches fenced path: ${rel}`);
    }
  }
}

async function applyPatch(patchText) {
  if (READONLY) throw new Error("server is read-only");
  if (typeof patchText !== "string" || patchText.length === 0) throw new Error("patch required");
  if (patchText.length > MAX_PATCH) throw new Error("patch too large");
  if (/^git\s/i.test(patchText.trim())) throw new Error("shell-style patch not allowed; use unified diff");
  assertPatchNotFenced(patchText);

  const patchFile = path.join(WORKSPACE, "output", "patch-inbox", `patch-${Date.now()}.patch`);
  fs.mkdirSync(path.dirname(patchFile), { recursive: true });
  fs.writeFileSync(patchFile, patchText, "utf8");

  const check = await git(["apply", "--check", "--whitespace=error-all", patchFile]);
  if (!check.ok) {
    fs.rmSync(patchFile, { force: true });
    throw new Error(`git apply --check failed: ${check.err || check.out}`);
  }
  const apply = await git(["apply", patchFile]);
  if (!apply.ok) {
    fs.rmSync(patchFile, { force: true });
    throw new Error(`git apply failed: ${apply.err || apply.out}`);
  }
  const status = await git(["status", "--short"]);
  return { applied: true, patchFile: path.relative(WORKSPACE, patchFile), status: status.out };
}

function send(res, code, body) {
  const payload = JSON.stringify(body);
  res.writeHead(code, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(payload),
    "Access-Control-Allow-Origin": process.env.APP_SERVER_CORS_ORIGIN ?? "*",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on("data", (c) => {
      size += c.length;
      if (size > MAX_BODY) { reject(new Error("body too large")); req.destroy(); return; }
      chunks.push(c);
    });
    req.on("end", () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}")); }
      catch { reject(new Error("invalid JSON")); }
    });
    req.on("error", reject);
  });
}

function authorize(req, res) {
  const header = req.headers.authorization ?? "";
  const match = /^Bearer\s+(.+)$/i.exec(header);
  if (!match || !safeEqual(match[1], TOKEN)) {
    send(res, 401, { error: "unauthorized" });
    return false;
  }
  return true;
}

const server = http.createServer(async (req, res) => {  const url = new URL(req.url, `http://${req.headers.host ?? "localhost"}`);
  const method = req.method;

  if (method === "OPTIONS") {
    send(res, 204, {});
    return;
  }

  // Health: no auth (probe only)
  if (method === "GET" && url.pathname === "/api/health") {
    const gitHead = await git(["rev-parse", "HEAD"]);
    send(res, 200, {
      ok: true,
      workspace: WORKSPACE,
      readonly: READONLY,
      head: gitHead.ok ? gitHead.out : "unknown",
      time: new Date().toISOString(),
    });
    return;
  }

  if (!authorize(req, res)) return;

  try {
    // GET /api/read?path=...
    if (method === "GET" && url.pathname === "/api/read") {
      const { full } = workspaceRelative(url.searchParams.get("path") ?? "");
      const { bytes, sha256 } = readFileSafe(full);
      send(res, 200, {
        path: url.searchParams.get("path"),
        bytes: bytes.byteLength,
        sha256,
        content: bytes.toString("utf8"),
      });
      return;
    }

    // GET /api/status — git status --short
    if (method === "GET" && url.pathname === "/api/status") {
      const status = await git(["status", "--short"]);
      send(res, 200, { ok: status.ok, status: status.out, head: (await git(["rev-parse", "HEAD"])).out });
      return;
    }

    // POST /api/apply — { patch: "<unified diff>" }  (dry_run: true to check only)
    if (method === "POST" && url.pathname === "/api/apply") {
      const body = await readBody(req);
      if (body.dry_run) {
        const patchText = String(body.patch ?? "");
        if (patchText.length > MAX_PATCH) throw new Error("patch too large");
        assertPatchNotFenced(patchText);
        const patchFile = path.join(WORKSPACE, "output", "patch-inbox", `dryrun-${Date.now()}.patch`);
        fs.mkdirSync(path.dirname(patchFile), { recursive: true });
        fs.writeFileSync(patchFile, patchText, "utf8");
        const check = await git(["apply", "--check", patchFile]);
        fs.rmSync(patchFile, { force: true });
        send(res, check.ok ? 200 : 422, { dry_run: true, ok: check.ok, error: check.ok ? null : (check.err || check.out) });
        return;
      }
      const result = await applyPatch(String(body.patch ?? ""));
      send(res, 200, result);
      return;
    }

    // POST /api/commit — { message, files?: [...] }  (commits staged/working changes)
    if (method === "POST" && url.pathname === "/api/commit") {
      if (READONLY) throw new Error("server is read-only");
      const body = await readBody(req);
      const message = String(body.message ?? "").trim();
      if (!message) throw new Error("commit message required");
      if (message.length > 500) throw new Error("commit message too long");
      const add = await git(["add", "-A"]);
      if (!add.ok) throw new Error(`git add failed: ${add.err}`);
      const commit = await git(["commit", "-m", message]);
      send(res, commit.ok ? 200 : 400, {
        ok: commit.ok,
        head: (await git(["rev-parse", "HEAD"])).out,
        error: commit.ok ? null : commit.out || commit.err,
      });
      return;
    }

    // POST /api/revert — revert the last local commit (bounded rescue)
    if (method === "POST" && url.pathname === "/api/revert") {
      if (READONLY) throw new Error("server is read-only");
      const revert = await git(["reset", "--soft", "HEAD~1"]);
      send(res, revert.ok ? 200 : 400, {
        ok: revert.ok,
        head: (await git(["rev-parse", "HEAD"])).out,
        error: revert.ok ? null : revert.err || revert.out,
      });
      return;
    }

    send(res, 404, { error: "not found" });
  } catch (error) {
    send(res, 400, { error: error.message });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[app-server] listening on http://127.0.0.1:${PORT}`);
  console.log(`[app-server] workspace: ${WORKSPACE}`);
  console.log(`[app-server] readonly: ${READONLY}`);
  console.log(`[app-server] endpoints: /api/health /api/read /api/status /api/apply /api/commit /api/revert`);
});

process.on("uncaughtException", (error) => {
  console.error("[app-server] uncaughtException:", error.message);
});
process.on("unhandledRejection", (error) => {
  console.error("[app-server] unhandledRejection:", error?.message ?? error);
});
