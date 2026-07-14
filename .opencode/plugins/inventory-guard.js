/**
 * Inventory Guard Plugin — enforces Rule 0 (read inventory.txt) programmatically.
 *
 * Three hooks:
 *   1. shell.env                       → injects project-critical paths as env vars
 *   2. tool.execute.before             → blocks pipeline runs if inventory wasn't read this session
 *   3. experimental.session.compacting → pins critical rules (Rule 0, Rule 1, Rule 2) in compaction context
 */

let inventoryReadThisSession = false;
let inventoryHash = null;
let formulaModifiedThisSession = false;
let pipelineRunThisSession = false;

export const InventoryGuard = async ({ project, client, $, directory, worktree }) => {
  return {

    // ── shell.env: inject project context ──────────────────────────────
    "shell.env": async (input, output) => {
      // Inject CI-safe defaults (extend env-guard pattern)
      output.env.OPENAI_API_KEY = output.env.OPENAI_API_KEY || "test-key";
      output.env.SECRET_KEY = output.env.SECRET_KEY || "test-secret-key-for-ci";

      // Inject project metadata
      output.env.PERFUME_INVENTORY_PATH = "inventory.txt";
      output.env.PERFUME_ODT_PATH = "engine/odor_thresholds.py";
      output.env.PERFUME_PROFILES_PATH = "engine/ingredient_intelligence.py";
      output.env.PERFUME_MATERIALS_DIR = "data/materials";
    },

    // ── tool.execute.before: enforce Rule 0 & pipeline pre-checks ──────
    "tool.execute.before": async (input, output) => {
      const tool = input.tool;
      const { args } = output;

      // Track when inventory.txt is read
      if (tool === "read" && args?.filePath) {
        const fp = String(args.filePath).replace(/\\/g, "/");
        if (fp.endsWith("inventory.txt")) {
          inventoryReadThisSession = true;
        }
      }

      // Track when inventory.txt is written (hash update trigger)
      if (tool === "write" && args?.filePath) {
        const fp = String(args.filePath).replace(/\\/g, "/");
        if (fp.endsWith("inventory.txt")) {
          inventoryReadThisSession = true; // writer implicitly knows inventory
        }
      }

      // Track formula file writes (markdown in formulas/ directory)
      if (tool === "write" && args?.filePath) {
        const fp = String(args.filePath).replace(/\\/g, "/");
        if (fp.startsWith("formulas/") && fp.endsWith(".md")) {
          formulaModifiedThisSession = true;
        }
      }

      // Block pipeline gate runs if inventory was never read
      if (tool === "bash" && args?.command) {
        const cmd = String(args.command);

        // Check for pipeline gate invocation
        if (cmd.includes("formula_release_gate.py")) {
          if (!inventoryReadThisSession) {
            throw new Error(
              "⛔ RULE 0 VIOLATION: You are trying to run the formula release gate without " +
              "reading inventory.txt this session.\n\n" +
              "Inventory changes between sessions. WHAT WAS AVAILABLE LAST WEEK MAY BE DEPLETED TODAY.\n\n" +
              "Required: Read inventory.txt before running any pipeline gate.\n" +
              "Run: /inventory or read inventory.txt directly, then retry."
            );
          }
          pipelineRunThisSession = true;
        }

        // Track format_pipeline_analysis runs
        if (cmd.includes("format_pipeline_analysis.py")) {
          pipelineRunThisSession = true;
        }

        // Block pipeline audit without inventory
        if (cmd.includes("pipeline_audit.py")) {
          if (!inventoryReadThisSession) {
            throw new Error(
              "⛔ RULE 0 VIOLATION: Read inventory.txt before running pipeline audit."
            );
          }
        }

        // ── PLAN F: Git commit guard ──────────────────────────────────
        if (cmd.startsWith("git commit") || cmd.includes("git commit")) {
          if (formulaModifiedThisSession && !pipelineRunThisSession) {
            console.warn(
              "⚠️  COMMIT GUARD: Formula files were modified this session but no pipeline " +
              "gate analysis was run.\n" +
              "  Modified formulas should have pipeline analysis appended under " +
              "'## Pipeline Analysis'.\n" +
              "  Run /gate <formula.md> <concentrate-ul> <brief> before committing.\n" +
              "  This is a WARNING — commit will proceed, but may lack validation."
            );
          }
        }

        // Warn on _generate_material_properties.py without inventory context
        if (cmd.includes("_generate_material_properties.py")) {
          if (!inventoryReadThisSession) {
            console.warn(
              "⚠️  Running material properties generation. Consider reading inventory.txt first " +
              "to ensure generated data matches current stock."
            );
          }
        }
      }

      // Prevent editing ODT_DATA without duplicate check
      if ((tool === "edit" || tool === "write") && args?.filePath) {
        const fp = String(args.filePath).replace(/\\/g, "/");
        if (fp.includes("odor_thresholds.py") && (tool === "edit")) {
          console.warn(
            "⚠️  Editing ODT_DATA. Remember: the LAST entry wins for duplicate keys.\n" +
            "Run /duplicate-odt-scanner after editing to check for conflicts."
          );
        }
      }
    },

    // ── experimental.session.compacting: pin critical context ──────────
    "experimental.session.compacting": async (input, output) => {
      const pinnedContext = [
        "RULES STILL ACTIVE:",
        "  RULE 0: Always read inventory.txt before formulating.",
        "  RULE 1: All calculations must use ppm, ODT, and OAV.",
        "  RULE 2: Never create new pipeline scripts.",
        `  INVENTORY READ THIS SESSION: ${inventoryReadThisSession ? "YES ✓" : "NO ✗"}`,
        "  Inventory path: inventory.txt",
        "  ODT path: engine/odor_thresholds.py",
        "  Material data: data/materials/<LETTER>.yaml",
        "  Profiles: engine/ingredient_intelligence.py",
      ].join("\n");

      output.context.push(pinnedContext);
    },
  };
};
