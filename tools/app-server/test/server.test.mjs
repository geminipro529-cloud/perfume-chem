// End-to-end tests for the app server: each run starts server.mjs against a
// throwaway git repository in the OS temp directory.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVER = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "server.mjs");
const TOKEN = "test-token";
const ALLOWED_ORIGIN = "https://allowed.example";
const TRAILER = "App-Server-Commit: perfume-chem-app-server";

// Child processes never inherit GIT_* variables, so git only ever sees the temp repo.
const cleanEnv = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("GIT_")));

let repo;
let server;
let base;

function git(...args) {
  assert.ok(repo.startsWith(fs.realpathSync(os.tmpdir())), "test repo must live in the temp dir");
  const r = spawnSync("git", args, { cwd: repo, env: cleanEnv, encoding: "utf8" });
  assert.equal(r.status, 0, `git ${args.join(" ")} failed: ${r.stderr}`);
  return r.stdout.trim();
}

function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.once("error", reject);
    s.listen(0, "127.0.0.1", () => {
      const { port } = s.address();
      s.close(() => resolve(port));
    });
  });
}

async function call(method, route, { body, auth = true, origin } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) headers.Authorization = `Bearer ${TOKEN}`;
  if (origin) headers.Origin = origin;
  const res = await fetch(base + route, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  return { status: res.status, headers: res.headers, text, json: text ? JSON.parse(text) : null };
}

before(async () => {
  repo = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "app-server-test-")));
  git("init", "-q", "-b", "main");
  git("config", "user.email", "test@example.invalid");
  git("config", "user.name", "Test");
  git("config", "commit.gpgsign", "false");
  fs.mkdirSync(path.join(repo, "src"));
  fs.writeFileSync(path.join(repo, "README.md"), "readme\n");
  fs.writeFileSync(path.join(repo, "src", "a.txt"), "alpha\n");
  fs.writeFileSync(path.join(repo, "src", "b.txt"), "bravo\n");
  fs.writeFileSync(path.join(repo, "src", "staged.txt"), "one\n");
  git("add", "-A");
  git("commit", "-q", "-m", "initial");

  const port = await freePort();
  base = `http://127.0.0.1:${port}`;
  server = spawn(process.execPath, [SERVER], {
    cwd: repo,
    env: {
      ...cleanEnv,
      APP_SERVER_ROOT: repo,
      APP_SERVER_PORT: String(port),
      APP_SERVER_TOKEN: TOKEN,
      APP_SERVER_CORS_ORIGINS: ALLOWED_ORIGIN,
    },
    stdio: "ignore",
  });
  for (let i = 0; i < 100; i++) {
    try {
      await fetch(`${base}/api/health`);
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 50));
    }
  }
  throw new Error("server did not start");
});

after(() => {
  server?.kill();
  if (repo) fs.rmSync(repo, { recursive: true, force: true });
});

test("unauthenticated health reveals no workspace path or HEAD", async () => {
  const r = await call("GET", "/api/health", { auth: false });
  assert.equal(r.status, 200);
  assert.equal(r.json.ok, true);
  assert.equal("workspace" in r.json, false);
  assert.equal("head" in r.json, false);
  assert.ok(!r.text.includes(repo));
  assert.ok(!r.text.includes(git("rev-parse", "HEAD")));
});

test("authenticated health still reports workspace and HEAD", async () => {
  const r = await call("GET", "/api/health");
  assert.equal(r.json.workspace, repo);
  assert.equal(r.json.head, git("rev-parse", "HEAD"));
});

test("CORS allow header only for configured origins", async () => {
  const evil = await call("GET", "/api/health", { auth: false, origin: "https://evil.example" });
  assert.equal(evil.headers.get("access-control-allow-origin"), null);
  const pre = await call("OPTIONS", "/api/apply", { auth: false, origin: "https://evil.example" });
  assert.equal(pre.headers.get("access-control-allow-origin"), null);
  const none = await call("GET", "/api/health", { auth: false });
  assert.equal(none.headers.get("access-control-allow-origin"), null);
  const ok = await call("GET", "/api/health", { auth: false, origin: ALLOWED_ORIGIN });
  assert.equal(ok.headers.get("access-control-allow-origin"), ALLOWED_ORIGIN);
});

test("patch renaming onto .env is refused by the fence", async () => {
  const patch = [
    "diff --git a/src/b.txt b/src/b.txt",
    "similarity index 100%",
    "rename from src/b.txt",
    "rename to .env",
    "",
  ].join("\n");
  const r = await call("POST", "/api/apply", { body: { patch } });
  assert.equal(r.status, 400);
  assert.match(r.json.error, /fenced/);
  assert.ok(fs.existsSync(path.join(repo, "src", "b.txt")));
  assert.ok(!fs.existsSync(path.join(repo, ".env")));
});

test("patch copying into .git/hooks is refused by the fence", async () => {
  const patch = [
    "diff --git a/src/a.txt b/src/a.txt",
    "similarity index 100%",
    "copy from src/a.txt",
    "copy to .git/hooks/x",
    "",
  ].join("\n");
  const r = await call("POST", "/api/apply", { body: { patch } });
  assert.equal(r.status, 400);
  assert.match(r.json.error, /fenced/);
  assert.ok(!fs.existsSync(path.join(repo, ".git", "hooks", "x")));
});

test("fence checks the b side of diff --git and non a/b prefixes", async () => {
  for (const patch of [
    "diff --git a/src/a.txt b/.env\nnew file mode 100644\n",
    "--- x/src/a.txt\n+++ y/.env\n@@ -0,0 +1 @@\n+k=v\n",
  ]) {
    const r = await call("POST", "/api/apply", { body: { patch, dry_run: true } });
    assert.equal(r.status, 400, patch);
    assert.match(r.json.error, /fenced/);
  }
});

test("revert is refused when HEAD is not a server commit", async () => {
  fs.writeFileSync(path.join(repo, "README.md"), "manual edit\n");
  git("commit", "-q", "-am", "manual commit", "-m", TRAILER); // forged trailer, unknown sha
  const head = git("rev-parse", "HEAD");
  const r = await call("POST", "/api/revert");
  assert.equal(r.status, 400);
  assert.match(r.json.error, /not a commit made by this server/);
  assert.equal(git("rev-parse", "HEAD"), head);
});

test("commit stages only patched paths, then revert undoes that commit", async () => {
  // Another agent's half-finished work: an untracked file, an unstaged edit, a staged edit.
  fs.writeFileSync(path.join(repo, "other.txt"), "wip\n");
  fs.writeFileSync(path.join(repo, "README.md"), "someone else's edit\n");
  fs.writeFileSync(path.join(repo, "src", "staged.txt"), "two\n");
  git("add", "src/staged.txt");

  const patch = [
    "diff --git a/src/a.txt b/src/a.txt",
    "--- a/src/a.txt",
    "+++ b/src/a.txt",
    "@@ -1 +1 @@",
    "-alpha",
    "+alpha2",
    "diff --git a/src/b.txt b/src/d.txt",
    "similarity index 100%",
    "rename from src/b.txt",
    "rename to src/d.txt",
    "",
  ].join("\n");
  const applied = await call("POST", "/api/apply", { body: { patch } });
  assert.equal(applied.status, 200, applied.text);

  const parent = git("rev-parse", "HEAD");
  const c = await call("POST", "/api/commit", { body: { message: "server change" } });
  assert.equal(c.status, 200, c.text);
  const files = git("show", "--no-renames", "--name-only", "--format=", "HEAD").split("\n").sort();
  assert.deepEqual(files, ["src/a.txt", "src/b.txt", "src/d.txt"]);
  assert.ok(git("log", "-1", "--format=%B").split("\n").includes(TRAILER));
  const status = git("status", "--porcelain");
  assert.match(status, /^\?\? other\.txt$/m);
  assert.deepEqual(git("diff", "--name-only").split("\n"), ["README.md"]);
  assert.deepEqual(git("diff", "--cached", "--name-only").split("\n"), ["src/staged.txt"]);

  const again = await call("POST", "/api/commit", { body: { message: "nothing new" } });
  assert.equal(again.status, 400);

  const r = await call("POST", "/api/revert");
  assert.equal(r.status, 200, r.text);
  assert.equal(git("rev-parse", "HEAD"), parent);

  const twice = await call("POST", "/api/revert");
  assert.equal(twice.status, 400);
  assert.equal(git("rev-parse", "HEAD"), parent);
});
