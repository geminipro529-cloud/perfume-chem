import path from "node:path";

export const EnvGuard = async ({ project, client, $, directory, worktree }) => {
  const resolveProjectPath = (value) => {
    const base = typeof directory === "string" ? directory : (directory?.path || process.cwd());
    return path.resolve(base, value);
  };

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath && output.args.filePath.includes(".env")) {
        const isExample = output.args.filePath.includes(".env.example")
        if (!isExample) {
          throw new Error("Do not read .env files — they contain secrets and API keys")
        }
      }
    },

    "shell.env": async (input, output) => {
      // Project-scoped keys are the only provider inputs accepted by OpenCode.
      if (process.env.PERFUME_DEEPINFRA_API_KEY) {
        output.env.DEEPINFRA_API_KEY = process.env.PERFUME_DEEPINFRA_API_KEY
      }
      if (process.env.PERFUME_DEEPSEEK_API_KEY) {
        output.env.DEEPSEEK_API_KEY = process.env.PERFUME_DEEPSEEK_API_KEY
      }
      if (process.env.OPENCODE_GO_API_KEY) {
        output.env.OPENCODE_GO_API_KEY = process.env.OPENCODE_GO_API_KEY
      }
      // Per-session isolation marker — runner.py refuses to operate if absent.
      output.env.OPENCODE_SESSION_ID = process.env.OPENCODE_SESSION_ID || "singleton_orphan"
      output.env.DEEPINFRA_SERVICE_TIER = process.env.DEEPINFRA_SERVICE_TIER || "standard"
      output.env.DEEPSEEK_SERVICE_TIER = process.env.DEEPSEEK_SERVICE_TIER || "standard"
      output.env.OPENAI_API_KEY = "test-key"
      output.env.SECRET_KEY = "test-secret-key-for-ci"
      output.env.PERFUME_INVENTORY = "inventory.txt"
      output.env.PERFUME_ODT = "engine/odor_thresholds.py"
      output.env.PERFUME_PROFILES = "engine/ingredient_intelligence.py"
      output.env.PERFUME_MATERIALS_DIR = resolveProjectPath("data/materials")
      output.env.PERFUME_PIPELINE_SCRIPT = resolveProjectPath("scripts/formula_release_gate.py")
      output.env.PERFUME_ANALYSIS_SCRIPT = resolveProjectPath("scripts/format_pipeline_analysis.py")
      output.env.PERFUME_INVENTORY = resolveProjectPath("inventory.txt")
      output.env.PERFUME_ODT = resolveProjectPath("engine/odor_thresholds.py")
      output.env.PERFUME_PROFILES = resolveProjectPath("engine/ingredient_intelligence.py")
    },

    "tool.execute.after": async (input, output) => {
      if (input.tool === "write" && input.args.filePath && input.args.filePath.includes(".env")) {
        const isExample = input.args.filePath.includes(".env.example")
        if (!isExample) {
          throw new Error("Do not write .env files — this could leak secrets")
        }
      }
    }
  }
}
