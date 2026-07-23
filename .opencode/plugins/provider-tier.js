export const ProviderTier = async ({ project, client, $, directory, worktree }) => {
  let pendingTier = "standard"

  function detectTier(input) {
    if (!input) return

    if (input.tool === "bash" && input.args?.command) {
      const cmd = input.args.command
      if (cmd.includes("formula_release_gate.py")) {
        pendingTier = "flex"
        return
      }
      if (cmd.includes("parallel/runner.py") && cmd.includes("--kind brain")) {
        pendingTier = "flex"
        return
      }
      if (cmd.includes("parallel/runner.py") && cmd.includes("--kind read")) {
        pendingTier = "flex"
        return
      }
    }
  }

  return {
    "tool.execute.before": async (input, output) => {
      pendingTier = "standard"
      detectTier({ tool: input.tool, args: output.args })
    },

    "shell.env": async (input, output) => {
      output.env.DEEPINFRA_SERVICE_TIER = process.env.DEEPINFRA_SERVICE_TIER || pendingTier
    },
  }
}
