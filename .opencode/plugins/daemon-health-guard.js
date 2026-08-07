/**
 * Daemon Health Guard Plugin — blocks cheapluna submissions when the project
 * daemon is degraded, and logs a guidance error routing the work to the local lane.
 *
 * Cheap local liveness check: the daemon writes a heartbeat/event into
 * .cheapluna-home/projects/perfume-chem-cheapluna/daemon-v2/scheduler.sqlite3
 * (events table) and the bridge requires an exact READY health probe before use.
 * This plugin does NOT call the MCP (that would recurse); it only checks the
 * on-disk daemon marker recency and refuses submissions when the daemon process
 * is absent or unhealthy, matching the recovery runbook (§8).
 */

import path from "node:path";
import fs from "node:fs";
import { execFileSync } from "node:child_process";

const SQLITE = ".opencode/.deepluna-home/projects/perfume-chem-cheapluna-isolated/daemon-v2/scheduler.sqlite3";
const STALE_MS = 5 * 60 * 1000;

function daemonHealthy(directory) {
  const db = path.resolve(directory || process.cwd(), SQLITE);
  if (!fs.existsSync(db)) return { ok: false, reason: "daemon sqlite missing" };
  try {
    const stat = fs.statSync(db);
    const age = Date.now() - stat.mtimeMs;
    if (age > STALE_MS) {
      return { ok: false, reason: `daemon sqlite stale (${Math.round(age / 1000)}s)` };
    }
    // Optional: query a recent event via python sqlite3 (read-only, bounded)
    const script =
      "import sqlite3;c=sqlite3.connect(r'" + db + "');" +
      "try:\n r=c.execute('SELECT MAX(created_at_ms) FROM events').fetchone()[0]\n" +
      " print(int(r or 0))\nexcept Exception:\n print(0)";
    const out = execFileSync("python", ["-c", script], { encoding: "utf8", timeout: 5000 }).trim();
    const lastEvent = parseInt(out || "0", 10);
    const nowMs = Date.now();
    if (nowMs - lastEvent > STALE_MS) {
      return { ok: false, reason: `no recent daemon event (last ${Math.round((nowMs - lastEvent) / 1000)}s)` };
    }
    return { ok: true, reason: "daemon healthy" };
  } catch (e) {
    return { ok: false, reason: `daemon check error: ${String(e).slice(0, 120)}` };
  }
}

export const DaemonHealthGuard = async ({ directory }) => {
  return {
    "tool.execute.before": async (input) => {
      const tool = input.tool;
      if (typeof tool !== "string" || !tool.startsWith("cheapluna_deepseek_")) return;
      const probeOnly = tool === "cheapluna_deepseek_check" || tool === "cheapluna_deepseek_metrics";
      if (probeOnly) return; // health/metrics calls are the diagnosis path themselves

      const health = daemonHealthy(directory);
      if (!health.ok) {
        throw new Error(
          `cheapluna health guard: daemon not healthy (${health.reason}). ` +
          `Do not submit. Route the wave to the local lane; attempt daemon restart per runbook §8; ` +
          `re-probe with cheapluna_deepseek_check before resuming.`
        );
      }
    },
  };
};
