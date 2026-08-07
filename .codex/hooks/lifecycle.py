"""Low-cost lifecycle audit hook for the Perfume-Chem Codex workspace."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / ".codex" / "runtime"
RETENTION_DAYS = 7
SAFE_FIELDS = (
    "hook_event_name",
    "session_id",
    "turn_id",
    "cwd",
    "model",
    "permission_mode",
    "source",
    "trigger",
    "tool_name",
    "agent_id",
    "agent_type",
    "tool_response_status",
)
EXPENSIVE_TOOL_NAMES = {
    "web.run",
    "deepseek_read_submit",
    "deepseek_write_submit",
    "deepseek_batch_submit",
    "deepseek_metrics",
    "tool_search_tool",
}
EXPENSIVE_COMMAND_MARKERS = (
    "project-verify",
    "pytest",
    "poetry run pytest",
    "poetry run mypy",
    "poetry run ruff",
    "npm install",
    "pip install",
    "docker compose",
)


def _bounded_string(value: object, limit: int = 240) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text[:limit]


def _prune_old_logs(now: datetime) -> None:
    cutoff = now.timestamp() - RETENTION_DAYS * 24 * 60 * 60
    for path in RUNTIME_DIR.glob("hooks-*.jsonl"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def _audit(payload: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    if payload.get("hook_event_name") == "SessionStart":
        _prune_old_logs(now)
    record: dict[str, object] = {
        "timestamp": now.isoformat(),
        "pid": os.getpid(),
    }
    for field in SAFE_FIELDS:
        value = _bounded_string(payload.get(field))
        if value is not None:
            record[field] = value

    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        # Record shape, never command text, prompts, file contents, or credentials.
        record["tool_input_keys"] = sorted(str(key)[:80] for key in tool_input)[:32]
        command = _bounded_string(tool_input.get("command"), limit=160)
        if command is not None:
            lowered = command.lower()
            record["command_cost_hint"] = next(
                (marker for marker in EXPENSIVE_COMMAND_MARKERS if marker in lowered),
                "cheap_or_unknown",
            )

    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        record["prompt_length"] = len(prompt)

    tool_name = str(payload.get("tool_name", ""))
    if tool_name:
        record["tool_cost_hint"] = (
            "external_or_expensive"
            if tool_name in EXPENSIVE_TOOL_NAMES or tool_name.startswith("mcp__")
            else "local_or_low"
        )

    path = RUNTIME_DIR / f"hooks-{now:%Y-%m-%d}.jsonl"
    line = json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n"
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, line.encode("utf-8"))
    finally:
        os.close(descriptor)


def _context_for(event: str) -> dict[str, object] | None:
    if event == "SessionStart":
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    "Perfume-Chem efficiency policy is active: read AGENTS.md; "
                    "research before implementation; use local tools before plugins; "
                    "reuse local/DeepLuna cache when inputs match; and choose the cheapest "
                    "verification or delegation that preserves quality."
                ),
            },
        }
    if event in {"UserPromptSubmit", "PreCompact", "PostCompact"}:
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": (
                    "Cost route: local rg/read/diff/focused tests first; DeepLuna READ with "
                    "reuse_cache=true for bounded extraction; Luna only through orchestrator "
                    "fallback; full verifier only for release-level claims."
                ),
            },
        }
    if event == "SubagentStart":
        return {
            "systemMessage": "Perfume-Chem cost and scope guardrails are active.",
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": (
                    "Stay within the assigned paths, preserve concurrent edits, and return evidence."
                ),
            },
        }
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
        _audit(payload)
        response = _context_for(str(payload.get("hook_event_name", "")))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=True))
        return 0
    except Exception as exc:  # Hooks must never break normal Codex operation.
        sys.stderr.write(f"perfume-chem lifecycle hook warning: {exc}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
