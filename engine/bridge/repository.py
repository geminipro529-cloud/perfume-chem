"""Confined, read-only repository search and fetch operations."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from engine.bridge.config import BridgeSettings
from engine.bridge.errors import BridgeBlocked

_ALLOWED_SUFFIXES = {
    ".cfg",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
_BLOCKED_SUFFIXES = {
    ".7z",
    ".crt",
    ".db",
    ".der",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
    ".png",
    ".sqlite",
    ".sqlite3",
    ".webp",
    ".xlsx",
    ".zip",
}
_BLOCKED_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519"}


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _relative_allowed(settings: BridgeSettings, relative_path: str) -> PurePosixPath:
    raw = relative_path.replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise BridgeBlocked("path traversal or absolute paths are not allowed")
    if any(part == ".git" for part in path.parts):
        raise BridgeBlocked("Git internals are not readable through the bridge")
    allowed = False
    for prefix in settings.allowed_read_prefixes:
        prefix_path = PurePosixPath(prefix.replace("\\", "/"))
        if path == prefix_path or prefix_path in path.parents:
            allowed = True
            break
    if not allowed:
        raise BridgeBlocked("path is outside the configured read prefixes")
    return path


def _resolve_text_file(settings: BridgeSettings, relative_path: str) -> tuple[Path, PurePosixPath]:
    relative = _relative_allowed(settings, relative_path)
    candidate = settings.repo_root.joinpath(*relative.parts)
    try:
        resolved_root = settings.repo_root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BridgeBlocked(f"file cannot be resolved: {exc}") from exc
    if not _is_within(resolved, resolved_root):
        raise BridgeBlocked("resolved path escapes the repository")
    if not resolved.is_file():
        raise BridgeBlocked("requested path is not a file")
    name = resolved.name.casefold()
    suffix = resolved.suffix.casefold()
    if name in _BLOCKED_NAMES or name.startswith(".env"):
        raise BridgeBlocked("environment and secret files are blocked")
    if suffix in _BLOCKED_SUFFIXES or suffix not in _ALLOWED_SUFFIXES:
        raise BridgeBlocked("requested file type is not allowlisted UTF-8 text")
    if resolved.stat().st_size > settings.max_read_bytes:
        raise BridgeBlocked("requested file exceeds the configured byte limit")
    return resolved, relative


def fetch_repository_file(
    settings: BridgeSettings,
    relative_path: str,
    *,
    max_chars: int = 20_000,
) -> dict[str, Any]:
    """Fetch one path-confined UTF-8 text file."""

    if max_chars < 1 or max_chars > settings.max_read_bytes:
        raise BridgeBlocked("max_chars is outside the permitted range")
    resolved, relative = _resolve_text_file(settings, relative_path)
    raw = resolved.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BridgeBlocked("requested file is not valid UTF-8 text") from exc
    return {
        "state": "PASS",
        "path": relative.as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "truncated": len(text) > max_chars,
        "content": text[:max_chars],
        "authority": "REPOSITORY_TEXT_READ_ONLY",
    }


def search_repository(
    settings: BridgeSettings,
    query: str,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Search allowlisted UTF-8 repository text with bounded traversal."""

    needle = query.strip()
    if len(needle) < 2 or len(needle) > 200:
        raise BridgeBlocked("query length must be between 2 and 200 characters")
    if limit < 1 or limit > 50:
        raise BridgeBlocked("limit must be between 1 and 50")

    matches: list[dict[str, Any]] = []
    files_examined = 0
    seen: set[Path] = set()
    folded = needle.casefold()
    for prefix in settings.allowed_read_prefixes:
        prefix_path = settings.repo_root.joinpath(*PurePosixPath(prefix).parts)
        if not prefix_path.exists():
            continue
        candidates = [prefix_path] if prefix_path.is_file() else sorted(prefix_path.rglob("*"))
        for candidate in candidates:
            if len(matches) >= limit or files_examined >= 2_000:
                break
            if not candidate.is_file() or candidate in seen:
                continue
            seen.add(candidate)
            try:
                relative = candidate.relative_to(settings.repo_root).as_posix()
                resolved, _ = _resolve_text_file(settings, relative)
            except (BridgeBlocked, ValueError):
                continue
            files_examined += 1
            try:
                text = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if folded in line.casefold():
                    matches.append(
                        {
                            "path": relative,
                            "line": line_number,
                            "snippet": line[:500],
                        }
                    )
                    if len(matches) >= limit:
                        break
        if len(matches) >= limit or files_examined >= 2_000:
            break
    return {
        "state": "PASS",
        "query": needle,
        "matches": matches,
        "files_examined": files_examined,
        "truncated": len(matches) >= limit or files_examined >= 2_000,
        "authority": "REPOSITORY_TEXT_READ_ONLY",
    }
