// Scoped filesystem MCP server for perfume-chem.
// Lets browser ChatGPT Pro / Codex read+write repo files through the Secure MCP Tunnel
// without GitHub. Security model mirrors the delegation daemon:
//  - Streamable HTTP on 127.0.0.1 only; every request must carry the per-launch bearer
//    token (FS_MCP_TOKEN, or a random one printed once at start), else 401.
//  - ALL paths are workspace-relative; absolute paths and escapes are rejected, also
//    after resolving symlinks. Secrets (.env*, *.pem, *.key, openai-api-key*, error.log)
//    and everything under .git/ are denied for reads and writes.
//  - Read-only by default; writes need FS_MCP_ALLOW_WRITES=1 or --allow-writes.
//  - Writes are exact-byte with SHA-256 verification returned to the caller.
//  - No shell execution.
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import http from "node:http";
import { fileURLToPath } from "node:url";
import {
  isAuthorized,
  isDeniedSegment,
  resolveAllowedPath,
  resolveToken,
  writesEnabled,
} from "./guard.mjs";

const DEFAULT_WORKSPACE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const WORKSPACE = process.env.FS_MCP_ROOT
  ? path.resolve(process.env.FS_MCP_ROOT)
  : DEFAULT_WORKSPACE;
const READONLY = !writesEnabled();
const PORT = Number(process.env.FS_MCP_PORT ?? 8765);
const MAX_READ_BYTES = Number(process.env.FS_MCP_MAX_READ_BYTES ?? 2_000_000);
const MAX_WRITE_BYTES = Number(process.env.FS_MCP_MAX_WRITE_BYTES ?? 1_000_000);

function normalizeAllowedPath(rel) {
  return resolveAllowedPath(WORKSPACE, rel);
}

function lstatNoFollow(full) {
  try {
    return fs.lstatSync(full);
  } catch {
    return null;
  }
}

function assertRegularFile(full) {
  const st = lstatNoFollow(full);
  if (!st) throw new Error("file does not exist");
  if (st.isSymbolicLink()) throw new Error("symbolic links are not allowed");
  if (!st.isFile()) throw new Error("not a regular file");
  return st;
}

function sha256Hex(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

async function listDirTree(full, depthLeft, results, prefix) {
  const st = lstatNoFollow(full);
  if (!st) return;
  if (st.isSymbolicLink()) return; // never traverse links
  if (st.isDirectory()) {
    results.push({ path: prefix || ".", type: "directory", size: null });
    if (depthLeft <= 0) return;
    const entries = fs.readdirSync(full).sort();
    for (const entry of entries) {
      if (isDeniedSegment(entry)) continue;
      const childFull = path.join(full, entry);
      const childPrefix = prefix ? `${prefix}/${entry}` : entry;
      await listDirTree(childFull, depthLeft - 1, results, childPrefix);
    }
  } else if (st.isFile()) {
    results.push({ path: prefix || ".", type: "file", size: st.size });
  }
}

function createServer() {
const server = new Server(
  { name: "perfume-chem-fs-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "read_file",
      description: `Read a workspace-relative file (up to ${MAX_READ_BYTES} bytes). Returns content, line count, and SHA-256. Paths must be relative to the workspace root.`,
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", description: "workspace-relative file path" },
          start_line: { type: "integer", description: "optional 1-based start line" },
          end_line: { type: "integer", description: "optional 1-based end line" },
        },
        required: ["path"],
      },
    },
    {
      name: "list_dir",
      description: "List a workspace-relative directory tree (depth limited).",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", description: "workspace-relative directory (default .)" },
          depth: { type: "integer", description: "max depth, default 2" },
        },
        required: [],
      },
    },
    {
      name: "search_text",
      description: "Case-sensitive text search over workspace files (line-oriented, no regex).",
      inputSchema: {
        type: "object",
        properties: {
          needle: { type: "string", description: "exact text to find" },
          path: { type: "string", description: "workspace-relative dir to search (default .)" },
          max_matches: { type: "integer", description: "default 50" },
        },
        required: ["needle"],
      },
    },
    {
      name: "write_file",
      description: `Write EXACT bytes to a workspace-relative file (up to ${MAX_WRITE_BYTES} bytes). Overwrites or creates. Returns SHA-256 + byte length. Use for new files or full rewrites.`,
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          content: { type: "string", description: "exact file content" },
        },
        required: ["path", "content"],
      },
    },
    {
      name: "edit_file",
      description: "Replace the FIRST occurrence of old_text with new_text in a workspace-relative file. old_text must be non-empty and present exactly once.",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          old_text: { type: "string", minLength: 1 },
          new_text: { type: "string" },
        },
        required: ["path", "old_text", "new_text"],
      },
    },
    {
      name: "file_info",
      description: "Return size, mtime, and SHA-256 for a workspace-relative file.",
      inputSchema: {
        type: "object",
        properties: { path: { type: "string" } },
        required: ["path"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    switch (name) {
      case "read_file": {
        const { rel, full } = normalizeAllowedPath(args.path);
        assertRegularFile(full);
        const bytes = fs.readFileSync(full);
        if (bytes.byteLength > MAX_READ_BYTES) {
          throw new Error(`file exceeds ${MAX_READ_BYTES} byte read limit`);
        }
        const text = bytes.toString("utf8");
        const lines = text.split("\n");
        const start = args.start_line ?? 1;
        const end = args.end_line ?? lines.length;
        const slice = lines.slice(Math.max(0, start - 1), Math.min(lines.length, end)).join("\n");
        return {
          content: [{ type: "text", text: JSON.stringify({
            path: rel,
            total_lines: lines.length,
            start_line: start,
            end_line: Math.min(end, lines.length),
            sha256: sha256Hex(bytes),
            bytes: bytes.byteLength,
            content: slice,
          }, null, 2) }],
        };
      }
      case "list_dir": {
        const rel = args.path ?? ".";
        const { full } = normalizeAllowedPath(rel);
        const st = lstatNoFollow(full);
        if (!st || !st.isDirectory()) throw new Error("directory does not exist");
        const results = [];
        await listDirTree(full, Number(args.depth ?? 2), results, rel === "." ? "." : rel);
        return { content: [{ type: "text", text: JSON.stringify({ path: rel, entries: results }, null, 2) }] };
      }
      case "search_text": {
        const needle = String(args.needle);
        const rel = args.path ?? ".";
        const { full } = normalizeAllowedPath(rel);
        const maxMatches = Number(args.max_matches ?? 50);
        const matches = [];
        const walk = (dir) => {
          const entries = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
          for (const entry of entries) {
            if (isDeniedSegment(entry.name) || entry.name === "node_modules" || entry.name === ".venv") continue;
            const child = path.join(dir, entry.name);
            if (entry.isSymbolicLink()) continue;
            if (entry.isDirectory()) walk(child);
            else if (entry.isFile() && child.endsWith(".md") || entry.isFile() && child.endsWith(".py") || entry.isFile() && child.endsWith(".js") || entry.isFile() && child.endsWith(".mjs") || entry.isFile() && child.endsWith(".json") || entry.isFile() && child.endsWith(".txt") || entry.isFile() && child.endsWith(".yaml") || entry.isFile() && child.endsWith(".toml")) {
              if (matches.length >= maxMatches) return;
              const lines = fs.readFileSync(child, "utf8").split("\n");
              for (let i = 0; i < lines.length; i++) {
                if (lines[i].includes(needle)) {
                  matches.push({ file: path.relative(WORKSPACE, child).replace(/\\/g, "/"), line: i + 1, text: lines[i].slice(0, 300) });
                  if (matches.length >= maxMatches) return;
                }
              }
            }
          }
        };
        walk(full);
        return { content: [{ type: "text", text: JSON.stringify({ needle, matches }, null, 2) }] };
      }
      case "write_file": {
        if (READONLY) throw new Error("server is read-only (start it with FS_MCP_ALLOW_WRITES=1 or --allow-writes to enable writes)");
        const { rel, full } = normalizeAllowedPath(args.path);
        const bytes = Buffer.from(String(args.content), "utf8");
        if (bytes.byteLength > MAX_WRITE_BYTES) throw new Error(`write exceeds ${MAX_WRITE_BYTES} byte limit`);
        const existing = lstatNoFollow(full);
        if (existing?.isSymbolicLink()) throw new Error("symbolic links are not allowed");
        fs.mkdirSync(path.dirname(full), { recursive: true });
        fs.writeFileSync(full, bytes);
        return {
          content: [{ type: "text", text: JSON.stringify({
            path: rel, bytes: bytes.byteLength, sha256: sha256Hex(bytes), written: true,
          }, null, 2) }],
        };
      }
      case "edit_file": {
        if (READONLY) throw new Error("server is read-only (start it with FS_MCP_ALLOW_WRITES=1 or --allow-writes to enable writes)");
        const { rel, full } = normalizeAllowedPath(args.path);
        assertRegularFile(full);
        const oldText = String(args.old_text);
        const newText = String(args.new_text);
        if (oldText.length === 0) throw new Error("old_text must be non-empty");
        const current = fs.readFileSync(full, "utf8");
        const first = current.indexOf(oldText);
        const second = current.indexOf(oldText, first + 1);
        if (first === -1) throw new Error("old_text not found in file");
        if (second !== -1) throw new Error("old_text appears more than once; use write_file for full rewrites");
        const updated = current.slice(0, first) + newText + current.slice(first + oldText.length);
        const bytes = Buffer.from(updated, "utf8");
        if (bytes.byteLength > MAX_WRITE_BYTES) throw new Error(`write exceeds ${MAX_WRITE_BYTES} byte limit`);
        fs.writeFileSync(full, bytes);
        return {
          content: [{ type: "text", text: JSON.stringify({
            path: rel, bytes: bytes.byteLength, sha256: sha256Hex(bytes), replaced: true,
          }, null, 2) }],
        };
      }
      case "file_info": {
        const { rel, full } = normalizeAllowedPath(args.path);
        assertRegularFile(full);
        const bytes = fs.readFileSync(full);
        return {
          content: [{ type: "text", text: JSON.stringify({
            path: rel, bytes: bytes.byteLength, sha256: sha256Hex(bytes), mtime_ms: fs.statSync(full).mtimeMs,
          }, null, 2) }],
        };
      }
      default:
        throw new Error(`unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      isError: true,
      content: [{ type: "text", text: `Error: ${error.message}` }],
    };
  }
});

return server;
}

const { token: TOKEN, generated } = resolveToken(process.env.FS_MCP_TOKEN);

const httpServer = http.createServer(async (req, res) => {
  if (!isAuthorized(req.headers.authorization, TOKEN)) {
    res.writeHead(401).end();
    return;
  }
  const { pathname } = new URL(req.url ?? "/", "http://127.0.0.1");
  if (pathname !== "/mcp") {
    res.writeHead(404).end();
    return;
  }
  // Stateless: a fresh server + transport per request, no MCP session IDs.
  const server = createServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on("close", () => {
    transport.close();
    server.close();
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res);
  } catch {
    if (!res.headersSent) res.writeHead(500).end();
  }
});

httpServer.listen(PORT, "127.0.0.1", () => {
  const { port } = httpServer.address();
  console.log(`perfume-chem-fs-mcp listening on http://127.0.0.1:${port}/mcp (${READONLY ? "read-only" : "WRITES ENABLED"})`);
  if (generated) {
    console.log(`Bearer token for this launch (send as "Authorization: Bearer <token>"): ${TOKEN}`);
  }
});
