export const GateCacheGuard = async ({ project, client, $, directory, worktree }) => {
  const CACHE_DIR = ".opencode/cache/gate_results"

  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool === "write" && input.args.filePath) {
        const fp = input.args.filePath
        if (fp.includes("formulas/") && fp.endsWith(".md")) {
          const hash = fp.replace(/[^a-zA-Z0-9]/g, "_").slice(0, 64)
          try {
            const cachePath = `${directory}/${CACHE_DIR}/${hash}.json`
            await $.fs.rm(cachePath, { force: true })
          } catch (_) {}
        }
      }
    },
  }
}
