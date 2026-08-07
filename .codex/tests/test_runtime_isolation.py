from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODEX_CONFIG = ROOT / ".codex" / "config.toml"
CODEX_NATIVE_CONFIG = ROOT / ".codex" / "config_codex_native.toml"
CODEX_DEEPLUNA_CONFIG = ROOT / ".codex" / "config_deepluna_fallback.toml"
OPENCODE_CONFIG = ROOT / "opencode.json"
ENV_GUARD = ROOT / ".opencode" / "plugins" / "env-guard.js"
DEEPLUNA_BOOTSTRAP = ROOT / "scripts" / "start_deepluna_codex.ps1"
DEEPLUNA_RUNTIME = ROOT / ".deepluna-home"
CHEAPLUNA_BOOTSTRAP = ROOT / "scripts" / "start_cheapluna_vscode.ps1"
CHEAPLUNA_BRIDGE = ROOT / ".opencode" / "scripts" / "cheapluna-bridge.ps1"
CHEAPLUNA_SKILL = (
    ROOT / ".opencode" / "skills" / "cheapluna-literature-review" / "SKILL.md"
)


class RuntimeIsolationTests(unittest.TestCase):
    # ── Two-config system ───────────────────────────────────────────

    def test_deepluna_fallback_config_has_all_env_vars(self) -> None:
        """config_deepluna_fallback.toml: GLM 5.2 primary + DeepLuna ON."""
        with CODEX_DEEPLUNA_CONFIG.open("rb") as handle:
            config = tomllib.load(handle)
        self.assertEqual(config["model"], "deepinfra/zai-org/GLM-5.2")
        self.assertEqual(config["model_reasoning_effort"], "high")
        server = config["mcp_servers"]["deepseek_orchestrator"]
        self.assertTrue(server["enabled"], "DeepLuna must be ON in fallback mode")
        self.assertEqual(server["env_vars"], ["DEEPINFRA_API_TOKEN"])
        self.assertIn("deepseek_check", server["enabled_tools"])
        self.assertEqual(server["env"]["DEEPLUNA_PRIMARY_PROFILE"], "deepinfra-fast")
        self.assertEqual(server["env"]["DEEPLUNA_FAST_ONLY"], "1")
        self.assertEqual(server["env"]["DEEPLUNA_CODEX_ORCHESTRATION"], "disabled")
        self.assertEqual(server["env"]["DEEPLUNA_READER_POOL_MODE"], "DYNAMIC")
        self.assertEqual(server["env"]["NANODRUG_DEEPINFRA_READER_LANES"], "5")
        self.assertEqual(server["env"]["DEEPLUNA_PROJECT_ID"], "perfume-chem")
        self.assertEqual(Path(server["env"]["DEEPSEEK_ORCHESTRATOR_HOME"]), DEEPLUNA_RUNTIME)
        self.assertEqual(Path(server["env"]["DEEPSEEK_ALLOWED_ROOT"]), ROOT)
        self.assertNotIn(".opencode", json.dumps(server).lower())

    def test_codex_native_config_has_deepluna_delegation_enabled(self) -> None:
        """config_codex_native.toml: gpt-5.6-sol + DeepLuna ON for subagent delegation."""
        with CODEX_NATIVE_CONFIG.open("rb") as handle:
            config = tomllib.load(handle)
        self.assertEqual(config["model"], "gpt-5.6-sol")
        self.assertEqual(config["model_reasoning_effort"], "high")
        server = config["mcp_servers"]["deepseek_orchestrator"]
        self.assertTrue(server["enabled"], "DeepLuna must be ON in native mode for delegation")
        self.assertEqual(
            server["env_vars"],
            ["DEEPINFRA_API_TOKEN"],
            "DEEPINFRA_API_TOKEN needed for delegation reads/writes",
        )
        self.assertIn("deepseek_check", server["enabled_tools"])
        self.assertEqual(server["env"]["DEEPLUNA_PRIMARY_PROFILE"], "deepinfra-fast")
        self.assertEqual(server["env"]["DEEPLUNA_FAST_ONLY"], "1")
        self.assertEqual(server["env"]["DEEPLUNA_CODEX_ORCHESTRATION"], "disabled")
        self.assertTrue(config["features"]["hooks"])
        self.assertFalse(config["features"]["plugins"])

    def test_active_config_matches_one_template(self) -> None:
        """config.toml must be byte-identical to one of the two templates."""
        active = CODEX_CONFIG.read_bytes()
        native = CODEX_NATIVE_CONFIG.read_bytes()
        fallback = CODEX_DEEPLUNA_CONFIG.read_bytes()
        self.assertTrue(
            active == native or active == fallback,
            "config.toml must match either config_codex_native.toml "
            "or config_deepluna_fallback.toml -- use swap_codex_config.ps1",
        )

    def test_both_configs_define_deepinfra_model_provider(self) -> None:
        """User-level ~/.codex/config.toml must declare [model_providers.deepinfra]
        so Codex auto-discovers GLM 5.2 and other DeepInfra-hosted models.
        Codex v0.145.0 only reads model_providers from the USER-level config,
        not project-local — hence the move from .codex/ to ~/.codex/."""
        user_config = Path.home() / ".codex" / "config.toml"
        self.assertTrue(user_config.exists(), f"Missing: {user_config}")
        with user_config.open("rb") as handle:
            config = tomllib.load(handle)
        self.assertIn("model_providers", config)
        provider = config["model_providers"]["deepinfra"]
        self.assertEqual(provider["name"], "DeepInfra")
        self.assertEqual(
            provider["base_url"],
            "https://api.deepinfra.com/v1/openai",
        )
        self.assertEqual(provider["env_key"], "DEEPINFRA_API_TOKEN")
        self.assertEqual(provider["wire_api"], "responses")
        self.assertFalse(provider.get("requires_openai_auth", False))

    # ── Bootstrap script ────────────────────────────────────────────

    def test_codex_deepluna_bootstrap_is_fail_closed_and_project_bound(self) -> None:
        script = DEEPLUNA_BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("DEEPLUNA_PROJECT_ID", script)
        self.assertIn("DEEPLUNA_PRIMARY_PROFILE", script)
        self.assertIn("deepinfra-fast", script)
        self.assertIn('"DEEPLUNA_FAST_ONLY" = "1"', script)
        self.assertIn('"DEEPLUNA_CODEX_ORCHESTRATION" = "disabled"', script)
        self.assertIn('"DEEPLUNA_READER_POOL_MODE" = "DYNAMIC"', script)
        self.assertIn('"NANODRUG_DEEPINFRA_READER_LANES" = "5"', script)
        self.assertIn("DEEPSEEK_ALLOWED_ROOT", script)
        self.assertIn("DEEPSEEK_ORCHESTRATOR_HOME", script)
        self.assertIn(".deepluna-home", script)
        self.assertIn("--project-id=perfume-chem", script)
        self.assertIn("--daemon", script)
        self.assertIn("connectProductionCandidateDaemon", script)
        self.assertIn("candidateDaemonPipeNameForProject", script)
        self.assertIn("getCandidateWindowsNamedPipeServerProcessId", script)
        self.assertIn("client.request('health', {})", script)
        self.assertIn("health.capacity?.read_limit !== 5", script)
        self.assertIn("health.capacity?.write_limit !== 1", script)
        self.assertIn("stale or incompatible daemon owns", script)
        self.assertIn("Refusing duplicate start", script)
        self.assertLess(
            script.index("getCandidateWindowsNamedPipeServerProcessId"),
            script.index("$daemonProcess = Start-Process"),
        )
        self.assertIn("the project daemon did not become READY", script)
        self.assertNotIn("Start-Sleep -Milliseconds 750", script)
        self.assertNotIn("Get-Content .env", script)
        self.assertNotIn("CODEX_HOME", script)

    def test_opencode_has_only_isolated_cheapluna_runtime(self) -> None:
        text = OPENCODE_CONFIG.read_text(encoding="utf-8")
        config = json.loads(text)
        self.assertNotIn("deepluna_read", config["mcp"])
        self.assertNotIn("deepluna_fast_read", config["mcp"])
        self.assertNotIn(r"C:\Users\ASUS\.codex".lower(), text.lower())
        self.assertNotIn("deepluna_read_*", text.lower())
        self.assertNotIn("deepluna_fast_read_*", text.lower())
        self.assertIn("cheapluna", config["mcp"])
        server = config["mcp"]["cheapluna"]
        self.assertEqual(server["type"], "local")
        self.assertTrue(server["enabled"])
        self.assertIn(
            ".opencode/scripts/cheapluna-bridge.ps1",
            " ".join(server["command"]),
        )
        self.assertIn("cheapluna", config["command"])
        self.assertIn("cheapluna-write", config["command"])
        for command_name in ("cheapluna", "cheapluna-write"):
            command_text = json.dumps(config["command"][command_name], sort_keys=True)
            self.assertIn("FLASH", command_text)
            self.assertIn("NO_LUNA", command_text)
            self.assertIn("maximum_attempts=1", command_text)
            self.assertIn("maximum_estimated_cost_usd<=0.01", command_text)
            self.assertIn("Never use Codex subagents", command_text)

    def test_cheapluna_is_fast_only_and_never_routes_to_codex_subagents(self) -> None:
        bootstrap = CHEAPLUNA_BOOTSTRAP.read_text(encoding="utf-8")
        bridge = CHEAPLUNA_BRIDGE.read_text(encoding="utf-8")
        skill = CHEAPLUNA_SKILL.read_text(encoding="utf-8")

        self.assertIn(".opencode\\scripts\\cheapluna-bridge.ps1", bootstrap)
        self.assertNotIn(r"\.codex\tools", bootstrap.lower())

        self.assertIn('DEEPLUNA_PRIMARY_PROFILE" = "deepinfra-fast"', bridge)
        self.assertIn('DEEPLUNA_FAST_ONLY" = "1"', bridge)
        self.assertIn(
            'DEEPLUNA_CODEX_ORCHESTRATION" = "disabled"',
            bridge,
        )
        self.assertIn('DEEPLUNA_EMBEDDED_COMPAT" = ""', bridge)
        self.assertIn("perfume-chem-cheapluna", bridge)
        self.assertIn(r"OpenCode\CheapLuna\runtime", bridge)
        self.assertIn(r"OpenCode\CheapLuna\state", bridge)
        self.assertIn(
            "b98f913fe8e87a17d697a86f0fe035eabef9517642dee1fe3f33651f76fdb44f",
            bridge,
        )
        self.assertIn("DEEPLUNA_CODEX_EXECUTABLE", bridge)
        self.assertIn("SetEnvironmentVariable", bridge)
        self.assertIn("foreign project daemon owner", bridge.lower())
        self.assertNotIn(r"\.codex\tools", bridge.lower())
        self.assertNotIn("deepseek-direct", bridge.lower())
        self.assertNotIn('DEEPLUNA_FAST_ONLY" = "0"', bridge)

        self.assertNotIn("tier: PRO", skill)
        self.assertNotIn("V4 Pro", skill)
        self.assertNotIn("LUNA_ELIGIBLE", skill)
        self.assertIn("FLASH", skill)
        self.assertIn("NO_LUNA", skill)
        self.assertIn("maximum_attempts=1", skill)
        self.assertIn("maximum_estimated_cost_usd<=0.01", skill)
        self.assertIn("Never use Codex subagents", skill)

    def test_opencode_uses_only_perfume_scoped_provider_inputs(self) -> None:
        guard = ENV_GUARD.read_text(encoding="utf-8")
        self.assertIn("process.env.PERFUME_DEEPINFRA_API_KEY", guard)
        self.assertIn("process.env.PERFUME_DEEPSEEK_API_KEY", guard)
        self.assertNotIn("process.env.DEEPINFRA_API_KEY", guard)
        self.assertNotIn("process.env.DEEPSEEK_API_KEY", guard)

    def test_obsolete_opencode_deepluna_surfaces_are_absent(self) -> None:
        for relative in (
            ".opencode/commands/deepluna.md",
            ".opencode/commands/deepluna-fast.md",
            ".opencode/agents/deepluna-reader.md",
            ".opencode/agents/deepluna-fast-reader.md",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()
