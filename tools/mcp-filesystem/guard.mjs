// Dependency-free access guards for the perfume-chem filesystem MCP server:
// per-launch bearer token, write opt-in, and the path deny-list.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export const MIN_TOKEN_LENGTH = 32;

// Returns { token, generated }. A supplied token must be long enough to resist guessing.
export function resolveToken(supplied) {
  if (supplied !== undefined && supplied !== "") {
    if (supplied.length < MIN_TOKEN_LENGTH) {
      throw new Error(`FS_MCP_TOKEN must be at least ${MIN_TOKEN_LENGTH} characters`);
    }
    return { token: supplied, generated: false };
  }
  return { token: crypto.randomBytes(32).toString("base64url"), generated: true };
}

function digest(value) {
  return crypto.createHash("sha256").update(String(value), "utf8").digest();
}

// Constant-time check of an `Authorization: Bearer <token>` header value.
export function isAuthorized(authorizationHeader, token) {
  if (typeof authorizationHeader !== "string" || typeof token !== "string" || token.length === 0) {
    return false;
  }
  const match = /^Bearer[ \t]+(\S+)[ \t]*$/i.exec(authorizationHeader);
  const presented = match ? match[1] : "";
  // Hash both sides so the comparison length never depends on the presented value.
  const equal = crypto.timingSafeEqual(digest(presented), digest(token));
  return equal && match !== null;
}

// Writes are refused unless the server was started with an explicit opt-in.
export function writesEnabled(env = process.env, argv = process.argv) {
  if (env.FS_MCP_READONLY === "1") return false;
  return env.FS_MCP_ALLOW_WRITES === "1" || argv.includes("--allow-writes");
}

// True when one path segment names something that must never be read or written.
export function isDeniedSegment(segment) {
  const s = segment.toLowerCase();
  return (
    s === ".git" ||
    s === ".env" ||
    s.startsWith(".env.") ||
    s.endsWith(".pem") ||
    s.endsWith(".key") ||
    s.includes("openai-api-key") ||
    s === "error.log"
  );
}

// `rel` is relative to the workspace; both slash styles and any case are treated alike.
export function isDeniedRelative(rel) {
  return String(rel)
    .split(/[\\/]+/)
    .some((segment) => segment.length > 0 && isDeniedSegment(segment));
}

// Real path of `full`, resolving symlinks in every existing ancestor (the leaf may not exist yet).
function realPathAllowingMissingLeaf(full) {
  const missing = [];
  let current = full;
  for (;;) {
    try {
      const real = fs.realpathSync.native(current);
      return missing.length ? path.join(real, ...missing.reverse()) : real;
    } catch (error) {
      if (error.code !== "ENOENT" && error.code !== "ENOTDIR") throw error;
      const parent = path.dirname(current);
      if (parent === current) return full;
      missing.push(path.basename(current));
      current = parent;
    }
  }
}

function within(root, candidate) {
  const caseFold = process.platform === "win32" || process.platform === "darwin";
  const r = caseFold ? root.toLowerCase() : root;
  const c = caseFold ? candidate.toLowerCase() : candidate;
  return c === r || c.startsWith(r.endsWith(path.sep) ? r : r + path.sep);
}

// Validates a workspace-relative path and returns { rel, full }. Rejects absolute paths,
// escapes (lexically and after resolving symlinks), and deny-listed names on either side.
export function resolveAllowedPath(workspace, rel) {
  if (typeof rel !== "string" || rel.length === 0) {
    throw new Error("path must be a non-empty string");
  }
  const forward = rel.replace(/\\/g, "/");
  if (path.isAbsolute(rel) || path.posix.isAbsolute(forward) || path.win32.isAbsolute(rel)) {
    throw new Error(`absolute paths are not allowed: ${rel}`);
  }
  const normalized = path.normalize(forward);
  const full = path.resolve(workspace, normalized);
  if (!within(workspace, full)) {
    throw new Error(`path escapes the workspace: ${rel}`);
  }
  if (isDeniedRelative(forward) || isDeniedRelative(path.relative(workspace, full))) {
    throw new Error(`path is denied: ${rel}`);
  }
  const realWorkspace = fs.realpathSync.native(workspace);
  const real = realPathAllowingMissingLeaf(full);
  if (!within(realWorkspace, real)) {
    throw new Error(`path escapes the workspace: ${rel}`);
  }
  if (isDeniedRelative(path.relative(realWorkspace, real))) {
    throw new Error(`path is denied: ${rel}`);
  }
  return { rel: normalized, full };
}
