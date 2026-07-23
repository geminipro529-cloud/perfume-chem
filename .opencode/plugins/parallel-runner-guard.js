export const ParallelRunnerGuard = async ({ project, client, $, directory, worktree }) => {
  return {
    "shell.env": async (input, output) => {
      if (!process.env.OPENCODE_SESSION_ID) {
        output.env.OPENCODE_SESSION_ID = `win_${process.pid}_${Date.now()}`
      }
    },

    "tool.execute.before": async (input, output) => {
      if (input.tool === "bash" && output.args.command) {
        const cmd = output.args.command
        if (cmd.includes("formula_release_gate.py") && !process.env.OPENCODE_SESSION_ID) {
          output.args.command = `echo "BLOCKED: OPENCODE_SESSION_ID unset. Set env before gating in multi-window mode." && exit 1`
        }
      }
    },
  }
}
