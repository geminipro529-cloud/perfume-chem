import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = (
    PROJECT_ROOT / ".opencode" / "scripts" / "cheapluna-chat-launcher.mjs"
)
OPENCODE_PATH = PROJECT_ROOT / "opencode.json"


def test_node_native_launcher_preserves_stdio_and_hides_helper_processes() -> None:
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")

    assert "await ensureExactProjectDaemon" in launcher
    assert "await main();" in launcher
    assert "windowsHide: true" in launcher
    assert 'stdio: ["ignore", "pipe", "ignore"]' in launcher
    assert 'stdio: "ignore"' in launcher
    assert "process.stdin" not in launcher
    assert "powershell.exe" in launcher
    assert "cheapluna-bridge.ps1" not in launcher


def test_all_runtime_routes_select_chat_and_disable_fast() -> None:
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
    opencode = json.loads(OPENCODE_PATH.read_text(encoding="utf-8"))
    command = opencode["mcp"]["cheapluna"]["command"]

    assert command == ["node", ".opencode/scripts/cheapluna-chat-launcher.mjs"]
    assert 'DEEPLUNA_PRIMARY_PROFILE: "cheapluna-chat"' in launcher
    assert 'DEEPLUNA_FAST_ONLY: "0"' in launcher
    assert "DIRECT_PRO" in OPENCODE_PATH.read_text(encoding="utf-8")
    assert "global-fast-launcher" not in " ".join(command)
