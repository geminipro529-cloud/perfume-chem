/**
 * CheapLuna Cache-First Plugin — exact-reuse short-circuit + cache manifest.
 *
 * Fingerprint = sha256(task_id + "\x00" + objective + "\x00" + sorted(required_read paths)).
 * When an identical submission has an accepted verdict in the manifest, the plugin
 * short-circuits (no provider call). On tool.execute.after it persists the outcome.
 *
 * Manifest: .opencode/cache/delegation_cache.json  (matches gate-cache-guard convention)
 */

import path from "node:path";
import fs from "node:fs";
import crypto from "node:crypto";

const MANIFEST_NAME = ".opencode/cache/delegation_cache.json";

function manifestPath(directory) {
  return path.resolve(directory || process.cwd(), MANIFEST_NAME);
}

function readManifest(directory) {
  try {
    const fp = manifestPath(directory);
    if (fs.existsSync(fp)) return JSON.parse(fs.readFileSync(fp, "utf8"));
  } catch (_) {}
  return { entries: {} };
}

function writeManifest(directory, manifest) {
  try {
    const fp = manifestPath(directory);
    fs.mkdirSync(path.dirname(fp), { recursive: true });
    fs.writeFileSync(fp, JSON.stringify(manifest, null, 1), "utf8");
  } catch (_) {}
}

function fingerprintOf(args) {
  if (!args) return null;
  const reads = Array.isArray(args.required_reads)
    ? args.required_reads.map((r) => r?.path || "").sort().join("|")
    : "";
  const raw = `${args.task_id || ""}\u0000${args.objective || ""}\u0000${reads}`;
  return crypto.createHash("sha256").update(raw, "utf8").digest("hex");
}

const ACCEPTED = new Set(["POSITIVE", "NEGATIVE", "NULL", "MIXED", "NOT_APPLICABLE", "CACHED"]);

export const CheapLunaCacheFirst = async ({ directory }) => {
  return {
    "tool.execute.before": async (input, output) => {
      const tool = input.tool;
      if (typeof tool !== "string") return;
      const single = tool === "cheapluna_deepseek_read_submit";
      const write = tool === "cheapluna_deepseek_write_submit";
      if (!single && !write) return;

      const args = output.args || {};
      const fp = fingerprintOf(args);
      if (!fp) return;
      const manifest = readManifest(directory);
      const hit = manifest.entries[fp];
      if (hit && ACCEPTED.has(hit.verdict)) {
        throw new Error(
          `cheapluna cache-first: exact-reuse short-circuit for ${args.task_id} ` +
          `(packet ${hit.packet || "?"}, verdict ${hit.verdict}, prior cost $${(hit.cost_usd || 0).toFixed(4)}). ` +
          `Reverify on disk; do NOT resubmit.`
        );
      }
    },

    "tool.execute.after": async (input, output) => {
      const tool = input.tool;
      if (typeof tool !== "string") return;
      if (tool !== "cheapluna_deepseek_job_status" && tool !== "cheapluna_deepseek_batch_status") return;
      const result = output?.result;
      if (!result) return;

      // Extract fingerprint from the originating submission is not available here;
      // persist only status outcomes keyed by job/batch id for auditability.
      try {
        const manifest = readManifest(directory);
        const batchId = result.batch_id;
        const jobId = result.job_id;
        if (batchId || jobId) {
          const key = `status:${batchId || jobId}`;
          manifest.entries[key] = {
            status: result.status,
            execution_status: result.execution_status,
            verdict: result.evidence_verdict,
            at: new Date().toISOString(),
          };
          writeManifest(directory, manifest);
        }
      } catch (_) {}
    },
  };
};
