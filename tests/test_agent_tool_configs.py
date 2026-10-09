"""Tracked agent configs: Codex stays sandboxed, OpenCode asks before risky git/delete commands."""

from __future__ import annotations

import fnmatch
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RISKY = [
    "git push",
    "git push origin master",
    "git push --force origin master",
    "git reset --hard",
    "git reset --hard HEAD~1",
    "git rebase -i HEAD~3",
    "rm -rf output/x",
    "rm -r build",
    "Remove-Item -Path x -Recurse -Force",
]
ORDINARY = ["pytest tests/", "python -m pytest -q", "git status", "git commit -m x"]


def _resolve(rules: object, command: str) -> str:
    """OpenCode bash permission: a string applies to all; otherwise last matching pattern wins."""
    if isinstance(rules, str):
        return rules
    assert isinstance(rules, dict)
    action = "ask"
    for pattern, value in rules.items():
        if fnmatch.fnmatchcase(command, pattern):
            action = value
    return action


def test_codex_config_is_workspace_sandboxed() -> None:
    text = (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
    config = tomllib.loads(text)
    assert "danger-full-access" not in text
    assert config["sandbox_mode"] == "workspace-write"
    assert config["approval_policy"] == "on-request"


def test_opencode_bash_permissions_ask_before_risky_commands() -> None:
    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    scopes = {"global": config["permission"]["bash"]}
    for name, agent in config["agent"].items():
        bash = agent.get("permission", {}).get("bash")
        if bash is not None and bash != "deny":
            scopes[name] = bash
    for name, rules in scopes.items():
        if _resolve(rules, "some-unlisted-command") != "allow":
            continue  # allowlist-style agents already gate everything else
        for command in RISKY:
            assert _resolve(rules, command) in {"ask", "deny"}, (name, command)
        for command in ORDINARY:
            assert _resolve(rules, command) == "allow", (name, command)
