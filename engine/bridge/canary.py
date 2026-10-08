"""Fixed-command, fail-closed provenance canary for Perfume-Chem."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from engine.bridge.config import BridgeSettings
from engine.bridge.receipts import seal_receipt

BRIDGE_VERSION = "1.0.0"
_VALID_MODES = {"metadata", "quick", "full"}
_SECRET_PATTERNS = (
    re.compile(r"(?i)https?://[^/@\s]+:[^/@\s]+@"),
    re.compile(r"(?i)(api[_-]?key|authorization|password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_tail(text: str, limit: int = 1_000) -> str:
    tail = text[-limit:]
    for pattern in _SECRET_PATTERNS:
        tail = pattern.sub("[REDACTED]", tail)
    return tail


def _command_result(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    retain_stdout: bool = False,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "returncode": None,
            "status": "FAIL",
            "stdout_sha256": _sha256_bytes(b""),
            "stderr_sha256": _sha256_bytes(str(exc).encode("utf-8")),
            "stdout_tail": "",
            "stderr_tail": _safe_tail(str(exc)),
        }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    public = {
        "returncode": completed.returncode,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "stdout_sha256": _sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": _sha256_bytes(stderr.encode("utf-8")),
        "stdout_tail": _safe_tail(stdout),
        "stderr_tail": _safe_tail(stderr),
    }
    if retain_stdout:
        public["_stdout_full"] = stdout
    return public


def normalize_github_origin(origin: str) -> str | None:
    """Normalize supported GitHub SSH/HTTPS origins to owner/repository."""

    value = origin.strip()
    if value.startswith("git@github.com:"):
        path = value.removeprefix("git@github.com:")
    else:
        parsed = urlparse(value)
        if parsed.hostname not in {"github.com", "www.github.com"}:
            return None
        path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    pieces = [part for part in path.split("/") if part]
    if len(pieces) != 2:
        return None
    return f"{pieces[0]}/{pieces[1]}"


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def verify_inventory(settings: BridgeSettings) -> dict[str, Any]:
    """Verify the exact byte and SHA-256 lock for Inventory V5."""

    path = settings.inventory_path
    result: dict[str, Any] = {
        "path": str(path),
        "expected_bytes": settings.inventory_bytes,
        "expected_sha256": settings.inventory_sha256,
        "authority": "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx",
        "status": "FAIL",
        "failures": [],
    }
    if not path.is_file():
        result["failures"] = ["missing"]
        return result
    actual_bytes = path.stat().st_size
    actual_sha = _sha256_file(path)
    failures: list[str] = []
    if actual_bytes != settings.inventory_bytes:
        failures.append("bytes")
    if actual_sha.lower() != settings.inventory_sha256.lower():
        failures.append("sha256")
    result.update(
        {
            "bytes": actual_bytes,
            "sha256": actual_sha,
            "failures": failures,
            "status": "PASS" if not failures else "FAIL",
        }
    )
    return result


def _verify_protocol(settings: BridgeSettings) -> dict[str, Any]:
    path = settings.repo_root / settings.protocol_relative_path
    result: dict[str, Any] = {
        "path": settings.protocol_relative_path.as_posix(),
        "expected_sha256": settings.protocol_sha256,
        "required_identity": "Chat Bridge Protocol v2.1",
        "status": "FAIL",
        "failures": [],
    }
    if settings.protocol_sha256 is None:
        result["failures"] = ["expected_sha256_not_configured"]
        return result
    if not path.is_file():
        result["failures"] = ["missing"]
        return result
    raw = path.read_bytes()
    actual_sha = _sha256_bytes(raw)
    actual_bytes = len(raw)
    failures: list[str] = []
    if actual_sha.lower() != settings.protocol_sha256.lower():
        failures.append("sha256")
    try:
        protocol_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        failures.append("utf8")
    else:
        if "Chat Bridge Protocol v2.1" not in protocol_text:
            failures.append("identity_marker")
    result.update(
        {
            "bytes": actual_bytes,
            "sha256": actual_sha,
            "failures": failures,
            "status": "PASS" if not failures else "FAIL",
        }
    )
    return result


def _git_value(settings: BridgeSettings, *arguments: str) -> tuple[str | None, dict[str, Any]]:
    command = ("git", "-C", str(settings.repo_root), *arguments)
    result = _command_result(
        command,
        cwd=settings.repo_root if settings.repo_root.exists() else Path.cwd(),
        timeout_seconds=min(settings.verify_timeout_seconds, 60),
        retain_stdout=True,
    )
    raw_stdout = result.pop("_stdout_full", "")
    value = raw_stdout.strip() if result["status"] == "PASS" else None
    return value, result


def _parse_worktrees(raw: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key in {"worktree", "HEAD", "branch", "detached", "bare", "locked", "prunable"}:
            current[key.lower()] = value.strip() if value else "true"
    if current:
        records.append(current)
    return records


def _repository_probe(settings: BridgeSettings) -> dict[str, Any]:
    result: dict[str, Any] = {
        "expected_root": str(settings.repo_root),
        "expected_repository": settings.expected_repository,
        "root_status": "FAIL",
        "origin_status": "FAIL",
        "dirty": None,
        "protected_path_changes": [],
        "worktrees": [],
        "failures": [],
    }
    root = settings.repo_root
    if not root.is_dir():
        result["failures"] = ["repository_root_missing"]
        return result

    resolved_root = root.resolve()
    for forbidden in settings.forbidden_roots:
        try:
            resolved_forbidden = forbidden.resolve()
        except OSError:
            resolved_forbidden = forbidden.absolute()
        if _same_path(resolved_root, resolved_forbidden) or _is_within(
            resolved_root, resolved_forbidden
        ):
            result["failures"].append("forbidden_repository_root")
            return result

    top, top_command = _git_value(settings, "rev-parse", "--show-toplevel")
    result["git_top_level_probe"] = top_command
    if top is None:
        result["failures"].append("not_a_git_repository")
        return result
    top_path = Path(top)
    if not _same_path(top_path, resolved_root):
        result["failures"].append("repository_root_mismatch")
        result["git_top_level"] = top
        return result
    result["root_status"] = "PASS"
    result["git_top_level"] = top

    origin, origin_command = _git_value(settings, "remote", "get-url", "origin")
    result["origin_probe"] = origin_command
    normalized = normalize_github_origin(origin or "")
    result["origin_transport"] = (
        "ssh" if (origin or "").startswith("git@") else urlparse(origin or "").scheme or "unknown"
    )
    result["origin_normalized"] = normalized
    if normalized and normalized.casefold() == settings.expected_repository.casefold():
        result["origin_status"] = "PASS"
    else:
        result["failures"].append("origin_mismatch")

    head, _ = _git_value(settings, "rev-parse", "HEAD")
    branch, branch_command = _git_value(settings, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch is None:
        branch = "DETACHED"
    status, _ = _git_value(settings, "status", "--porcelain=v1", "--untracked-files=all")
    worktrees, _ = _git_value(settings, "worktree", "list", "--porcelain")
    dirty_lines = [line for line in (status or "").splitlines() if line.strip()]
    protected_prefixes = ("engine/", "backend/", ".github/", "data/", "chat_bridge/")
    protected_changes = []
    for line in dirty_lines:
        path_text = line[3:].split(" -> ")[-1].replace("\\", "/") if len(line) >= 4 else line
        if path_text.startswith(protected_prefixes):
            protected_changes.append(path_text)

    result.update(
        {
            "head": head,
            "branch": branch,
            "branch_probe": branch_command,
            "dirty": bool(dirty_lines),
            "dirty_entry_count": len(dirty_lines),
            "protected_path_changes": protected_changes,
            "worktrees": _parse_worktrees(worktrees or ""),
        }
    )
    if not head:
        result["failures"].append("head_unresolved")
    if dirty_lines:
        result["failures"].append("dirty_worktree")
    return result


def _workbench_probe(settings: BridgeSettings) -> dict[str, Any]:
    command = (
        sys.executable,
        "-c",
        "from engine.workbench import PerfumeWorkbench; print(PerfumeWorkbench.__name__)",
    )
    result = _command_result(
        command,
        cwd=settings.repo_root,
        timeout_seconds=min(settings.verify_timeout_seconds, 120),
    )
    return {"command": list(command), **result}


def _migration_probe(settings: BridgeSettings) -> dict[str, Any]:
    candidates = (
        settings.repo_root / "backend" / "alembic.ini",
        settings.repo_root / "alembic.ini",
    )
    config_path = next((path for path in candidates if path.is_file()), None)
    if config_path is None:
        return {
            "status": "NOT_APPLICABLE",
            "reason": "no alembic.ini present",
            "heads": [],
        }
    cwd = config_path.parent
    command = (sys.executable, "-m", "alembic", "-c", config_path.name, "heads")
    result = _command_result(
        command,
        cwd=cwd,
        timeout_seconds=min(settings.verify_timeout_seconds, 120),
    )
    heads = [line.strip() for line in result["stdout_tail"].splitlines() if line.strip()]
    return {"command": list(command), "heads": heads, **result}


def _extract_verification_pass(stdout_tail: str) -> bool:
    text = stdout_tail.strip()
    if not text:
        return False
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    failed = payload.get("failed")
    if isinstance(failed, list) and failed:
        return False
    checks = payload.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            if check.get("required", True) and check.get("status") == "FAIL":
                return False
    return True


def _verification_probe(settings: BridgeSettings, mode: str) -> dict[str, Any]:
    if mode == "metadata":
        return {
            "mode": mode,
            "status": "NOT_RUN",
            "reason": "metadata mode cannot verify repository acceptance checks",
            "command": [],
        }
    script = settings.repo_root / "scripts" / "pipeline_audit.py"
    command = [
        sys.executable,
        "scripts/pipeline_audit.py",
        "project-verify",
    ]
    if mode == "quick":
        command.append("--quick")
    command.append("--json")
    if not script.is_file():
        return {
            "mode": mode,
            "status": "FAIL",
            "reason": "scripts/pipeline_audit.py is missing",
            "command": command,
        }
    result = _command_result(
        command,
        cwd=settings.repo_root,
        timeout_seconds=settings.verify_timeout_seconds,
        retain_stdout=True,
    )
    full_stdout = result.pop("_stdout_full", "")
    accepted = result["status"] == "PASS" and _extract_verification_pass(
        full_stdout
    )
    return {
        "mode": mode,
        "command": command,
        **result,
        "status": "PASS" if accepted else "FAIL",
    }


def run_canary(settings: BridgeSettings, mode: str = "metadata") -> dict[str, Any]:
    """Run the selected bridge canary and return a sealed provenance receipt."""

    if mode not in _VALID_MODES:
        raise ValueError(f"unsupported canary mode: {mode}")

    repository_preflight = _repository_probe(settings)
    inventory = verify_inventory(settings)
    protocol = _verify_protocol(settings)

    if repository_preflight.get("root_status") == "PASS":
        workbench = _workbench_probe(settings)
        migrations = _migration_probe(settings)
        verification = _verification_probe(settings, mode)
        repository = _repository_probe(settings)
        preflight_summary = {
            "root_status": repository_preflight.get("root_status"),
            "origin_status": repository_preflight.get("origin_status"),
            "origin_normalized": repository_preflight.get("origin_normalized"),
            "head": repository_preflight.get("head"),
            "branch": repository_preflight.get("branch"),
            "dirty": repository_preflight.get("dirty"),
        }
        repository["preflight"] = preflight_summary
        repository["head_unchanged"] = (
            bool(repository_preflight.get("head"))
            and repository_preflight.get("head") == repository.get("head")
        )
        repository["branch_unchanged"] = (
            repository_preflight.get("branch") == repository.get("branch")
        )
        repository["origin_unchanged"] = (
            repository_preflight.get("origin_normalized")
            == repository.get("origin_normalized")
        )
        if not repository["head_unchanged"]:
            repository.setdefault("failures", []).append("head_changed_during_canary")
        if not repository["branch_unchanged"]:
            repository.setdefault("failures", []).append("branch_changed_during_canary")
        if not repository["origin_unchanged"]:
            repository.setdefault("failures", []).append("origin_changed_during_canary")
    else:
        repository = dict(repository_preflight)
        repository["preflight"] = {
            "root_status": repository_preflight.get("root_status"),
            "origin_status": repository_preflight.get("origin_status"),
            "origin_normalized": repository_preflight.get("origin_normalized"),
            "head": repository_preflight.get("head"),
            "branch": repository_preflight.get("branch"),
            "dirty": repository_preflight.get("dirty"),
        }
        repository["head_unchanged"] = False
        repository["branch_unchanged"] = False
        repository["origin_unchanged"] = False
        workbench = {"status": "FAIL", "reason": "repository root probe failed"}
        migrations = {"status": "NOT_RUN", "reason": "repository root probe failed"}
        verification = {
            "mode": mode,
            "status": "NOT_RUN" if mode == "metadata" else "FAIL",
            "reason": "repository root probe failed",
            "command": [],
        }

    metadata_pass = all(
        (
            repository_preflight.get("root_status") == "PASS",
            repository_preflight.get("origin_status") == "PASS",
            repository_preflight.get("dirty") is False,
            bool(repository_preflight.get("head")),
            repository.get("root_status") == "PASS",
            repository.get("origin_status") == "PASS",
            repository.get("dirty") is False,
            bool(repository.get("head")),
            repository.get("head_unchanged") is True,
            repository.get("branch_unchanged") is True,
            repository.get("origin_unchanged") is True,
            inventory.get("status") == "PASS",
            protocol.get("status") == "PASS",
            workbench.get("status") == "PASS",
            migrations.get("status") in {"PASS", "NOT_APPLICABLE"},
        )
    )
    if not metadata_pass:
        state = "BRIDGE_BLOCKED"
    elif mode == "metadata":
        state = "READY_FOR_VERIFICATION"
    elif verification.get("status") == "PASS":
        state = "PASS"
    else:
        state = "BRIDGE_BLOCKED"

    payload: dict[str, Any] = {
        "schema": "perfume-chem-bridge-canary-v1",
        "bridge_version": BRIDGE_VERSION,
        "generated_at_utc": _utc_now(),
        "canary_mode": mode,
        "state": state,
        "repository": repository,
        "inventory": inventory,
        "protocol": protocol,
        "runtime": {
            "python_executable": sys.executable,
            "python_version": ".".join(str(part) for part in sys.version_info[:3]),
            "workbench_import": workbench,
            "migration_heads": migrations,
        },
        "verification": verification,
        "security": {
            "packet_writes_enabled": settings.packet_writes_enabled,
            "write_tool_exposed": settings.expose_write_tool,
            "signing_key_configured": settings.signing_key is not None,
            "secrets_exposed": False,
            "arbitrary_command_execution": False,
            "canonical_mutation_authorized": False,
            "formula_mutation_authorized": False,
        },
        "withheld_claims": [
            "local bridge access until this canary passes on the real repository",
            "canonical promotion",
            "formula mutation",
            "physical liking",
            "similarity",
            "stability",
            "safety",
            "measured headspace",
            "strict empirical OAV",
            "release readiness",
        ],
    }
    return seal_receipt(payload, settings.signing_key)
