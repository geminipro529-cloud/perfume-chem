// Run from tools/mcp-filesystem after `npm ci`: node --test test/
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const SERVER = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "server.mjs");
const TOKEN = "t".repeat(20) + "0123456789abcdefXYZ";

let tmp;
let root;
const servers = [];

function writeFile(rel, content = "secret") {
  const full = path.join(root, rel);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content);
}

before(() => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), "fs-mcp-test-"));
  root = path.join(tmp, "workspace");
  fs.mkdirSync(root);
  writeFile("formulas/x.md", "# ordinary formula\n");
  writeFile(".env");
  writeFile(".env.local");
  writeFile("x.pem");
  writeFile("openai-api-key.txt");
  writeFile("error.log");
  writeFile(".git/hooks/pre-push");
  fs.symlinkSync(path.join(root, ".env"), path.join(root, "innocent.txt"));
  fs.symlinkSync(path.join(root, ".git"), path.join(root, "gitlink"));
  fs.mkdirSync(path.join(tmp, "outside"));
  fs.writeFileSync(path.join(tmp, "outside", "o.txt"), "outside");
  fs.symlinkSync(path.join(tmp, "outside"), path.join(root, "outlink"));
});

after(() => {
  for (const child of servers) child.kill();
  fs.rmSync(tmp, { recursive: true, force: true });
});

async function startServer(extraEnv = {}, args = []) {
  const child = spawn(process.execPath, [SERVER, ...args], {
    env: { PATH: process.env.PATH, FS_MCP_ROOT: root, FS_MCP_PORT: "0", ...extraEnv },
    stdio: ["ignore", "pipe", "pipe"],
  });
  servers.push(child);
  let out = "";
  const url = await new Promise((resolve, reject) => {
    child.stdout.on("data", (chunk) => {
      out += chunk;
      const m = /listening on (http:\/\/127\.0\.0\.1:\d+\/mcp)/.exec(out);
      if (m) setTimeout(() => resolve(m[1]), 50);
    });
    child.on("exit", (code) => reject(new Error(`server exited ${code}`)));
  });
  return { url, stdout: () => out };
}

async function connect(url, token) {
  const client = new Client({ name: "test", version: "1.0.0" });
  await client.connect(
    new StreamableHTTPClientTransport(new URL(url), {
      requestInit: { headers: { Authorization: `Bearer ${token}` } },
    }),
  );
  return client;
}

async function call(client, name, args) {
  const result = await client.callTool({ name, arguments: args });
  return { isError: Boolean(result.isError), text: result.content[0].text };
}

const initBody = JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "t", version: "1" } },
});

async function rawPost(url, headers) {
  return fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json, text/event-stream", ...headers },
    body: initBody,
  });
}

test("no token and wrong token get a bare 401; right token is allowed", async () => {
  const { url } = await startServer({ FS_MCP_TOKEN: TOKEN });
  const none = await rawPost(url, {});
  assert.equal(none.status, 401);
  assert.equal(await none.text(), "");
  const wrong = await rawPost(url, { authorization: `Bearer ${TOKEN}x` });
  assert.equal(wrong.status, 401);
  assert.equal(await wrong.text(), "");
  const otherPath = await fetch(url.replace("/mcp", "/anything"));
  assert.equal(otherPath.status, 401);
  const right = await rawPost(url, { authorization: `Bearer ${TOKEN}` });
  assert.equal(right.status, 200);
  await right.body?.cancel();
});

test("a generated per-launch token is printed once and works", async () => {
  const { url, stdout } = await startServer({});
  const m = /Bearer token for this launch .*?\): (\S+)/.exec(stdout());
  assert.ok(m, "token printed");
  assert.match(m[1], /^[A-Za-z0-9_-]{43}$/);
  assert.equal(stdout().split(m[1]).length - 1, 1);
  const client = await connect(url, m[1]);
  const r = await call(client, "read_file", { path: "formulas/x.md" });
  assert.equal(r.isError, false);
  await client.close();
});

test("write tools are refused without the opt-in", async () => {
  const { url } = await startServer({ FS_MCP_TOKEN: TOKEN });
  const client = await connect(url, TOKEN);
  const w = await call(client, "write_file", { path: "formulas/new.md", content: "x" });
  assert.equal(w.isError, true);
  assert.match(w.text, /read-only/);
  const e = await call(client, "edit_file", { path: "formulas/x.md", old_text: "ordinary", new_text: "changed" });
  assert.equal(e.isError, true);
  assert.equal(fs.existsSync(path.join(root, "formulas/new.md")), false);
  assert.equal(fs.readFileSync(path.join(root, "formulas/x.md"), "utf8"), "# ordinary formula\n");
  await client.close();
});

test("write tools work with the opt-in, but never on denied paths", async () => {
  for (const opt of [{ env: { FS_MCP_ALLOW_WRITES: "1" }, args: [] }, { env: {}, args: ["--allow-writes"] }]) {
    const { url } = await startServer({ FS_MCP_TOKEN: TOKEN, ...opt.env }, opt.args);
    const client = await connect(url, TOKEN);
    const w = await call(client, "write_file", { path: "formulas/new.md", content: "new" });
    assert.equal(w.isError, false, w.text);
    assert.equal(fs.readFileSync(path.join(root, "formulas/new.md"), "utf8"), "new");
    fs.rmSync(path.join(root, "formulas/new.md"));
    for (const denied of [".git/hooks/pre-push", ".env", "gitlink/hooks/post-commit"]) {
      const d = await call(client, "write_file", { path: denied, content: "pwned" });
      assert.equal(d.isError, true, denied);
      assert.match(d.text, /denied/, denied);
    }
    assert.equal(fs.readFileSync(path.join(root, ".git/hooks/pre-push"), "utf8"), "secret");
    assert.equal(fs.existsSync(path.join(root, ".git/hooks/post-commit")), false);
    await client.close();
  }
});

test("deny-list blocks secrets and .git for reads; ordinary files stay readable", async () => {
  const { url } = await startServer({ FS_MCP_TOKEN: TOKEN });
  const client = await connect(url, TOKEN);
  const denied = [
    ".env",
    ".env.local",
    "x.pem",
    "openai-api-key.txt",
    "error.log",
    ".git/hooks/pre-push",
    "sub/../.env",
    ".GIT\\hooks\\pre-push",
    "innocent.txt",
    "gitlink/hooks/pre-push",
  ];
  for (const p of denied) {
    for (const tool of ["read_file", "file_info"]) {
      const r = await call(client, tool, { path: p });
      assert.equal(r.isError, true, `${tool} ${p}`);
      assert.match(r.text, /path is denied/, `${tool} ${p}`);
    }
  }
  const listGit = await call(client, "list_dir", { path: ".git" });
  assert.match(listGit.text, /path is denied/);
  const outside = await call(client, "read_file", { path: "outlink/o.txt" });
  assert.match(outside.text, /escapes the workspace/);
  const dotdot = await call(client, "read_file", { path: "../outside/o.txt" });
  assert.match(dotdot.text, /escapes the workspace/);

  const ok = await call(client, "read_file", { path: "formulas/x.md" });
  assert.equal(ok.isError, false);
  assert.equal(JSON.parse(ok.text).content, "# ordinary formula\n");

  const listing = JSON.parse((await call(client, "list_dir", { path: ".", depth: 3 })).text);
  const names = listing.entries.map((e) => e.path);
  assert.ok(names.includes("./formulas/x.md"));
  for (const hidden of [".env", ".env.local", "x.pem", "openai-api-key.txt", "error.log", ".git"]) {
    assert.ok(!names.includes(`./${hidden}`), hidden);
  }
  const search = JSON.parse((await call(client, "search_text", { needle: "secret" })).text);
  assert.deepEqual(search.matches, []);
  await client.close();
});
