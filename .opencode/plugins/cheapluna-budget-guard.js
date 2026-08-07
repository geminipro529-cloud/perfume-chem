/**
 * CheapLuna Budget Guard Plugin — validates the §4 token/budget envelope before
 * any cheapluna_* submission, and logs per-call budget facts.
 *
 * Envelope (COST-DEPTH-20260805 plan):
 *   max_output_tokens        3000-8192
 *   maximum_attempts         1
 *   maximum_provider_calls   2 (probe: 1)
 *   required_reads total     <= 15KB (probe <= 2KB)
 *   maximum_estimated_cost_usd <= 0.05 read / 0.08 write / 0.01 probe
 *   maximum_input_tokens     <= 40k (route)
 */

import path from "node:path";
import fs from "node:fs";

const LOG_DIR = ".opencode/cache/delegation_budget";

function logLine(directory, entry) {
  try {
    const dir = path.resolve(directory || process.cwd(), LOG_DIR);
    fs.mkdirSync(dir, { recursive: true });
    const file = path.join(dir, "budget.jsonl");
    fs.appendFileSync(file, JSON.stringify(entry) + "\n", "utf8");
  } catch (_) {}
}

function estimateReadBytes(directory, reads) {
  let total = 0;
  if (!Array.isArray(reads)) return 0;
  for (const r of reads) {
    if (!r?.path) continue;
    try {
      const fp = path.resolve(directory || process.cwd(), r.path);
      if (fs.existsSync(fp)) total += fs.statSync(fp).size;
    } catch (_) {}
  }
  return total;
}

export const CheapLunaBudgetGuard = async ({ directory }) => {
  return {
    "tool.execute.before": async (input, output) => {
      const tool = input.tool;
      if (typeof tool !== "string" || !tool.startsWith("cheapluna_deepseek_")) return;

      const args = output.args || {};
      const entry = {
        tool,
        task_id: args.task_id || (Array.isArray(args.tasks) ? args.tasks.length : undefined),
        at: new Date().toISOString(),
        violations: [],
      };

      // Probe jobs (no required_reads) are the only 1-call jobs; read jobs 2 calls max.
      if (Array.isArray(args.tasks)) {
        // batch submission — validate each task
        for (const t of args.tasks) {
          if (t.maximum_attempts != null && t.maximum_attempts !== 1) {
            entry.violations.push(`task ${t.node_id}: maximum_attempts=${t.maximum_attempts} != 1`);
          }
          if (t.maximum_provider_calls != null && t.maximum_provider_calls > 2) {
            entry.violations.push(`task ${t.node_id}: maximum_provider_calls=${t.maximum_provider_calls} > 2`);
          }
          const bytes = estimateReadBytes(directory, t.required_reads);
          if (bytes > 15 * 1024) {
            entry.violations.push(`task ${t.node_id}: reads=${(bytes / 1024).toFixed(1)}KB > 15KB`);
          }
          const cost = t.route_constraints?.maximum_estimated_cost_usd;
          if (cost != null && cost > 0.08) {
            entry.violations.push(`task ${t.node_id}: max_cost=${cost} > 0.08`);
          }
        }
      } else {
        const isProbe = (args.max_output_tokens || 0) <= 3000 && !args.required_reads?.length;
        if (args.maximum_attempts != null && args.maximum_attempts !== 1) {
          entry.violations.push(`maximum_attempts=${args.maximum_attempts} != 1`);
        }
        const calls = args.route_constraints?.maximum_provider_calls;
        const callsOk = isProbe ? calls === 1 : (calls == null || calls <= 2);
        if (!callsOk) {
          entry.violations.push(`maximum_provider_calls=${calls} (probe must be 1, read <= 2)`);
        }
        const bytes = estimateReadBytes(directory, args.required_reads);
        const readCap = isProbe ? 2 * 1024 : 15 * 1024;
        if (bytes > readCap) {
          entry.violations.push(`reads=${(bytes / 1024).toFixed(1)}KB > ${(readCap / 1024)}KB`);
        }
        const cost = args.route_constraints?.maximum_estimated_cost_usd;
        const costCap = isProbe ? 0.01 : 0.08;
        if (cost != null && cost > costCap) {
          entry.violations.push(`max_cost=${cost} > ${costCap}`);
        }
      }

      logLine(directory, entry);
      if (entry.violations.length > 0) {
        throw new Error(
          "cheapluna budget guard: " + entry.violations.join("; ") +
          " (see COST-DEPTH-20260805 plan §4)"
        );
      }
    },
  };
};
