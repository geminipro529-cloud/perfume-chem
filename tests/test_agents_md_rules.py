"""Guards against AGENTS.md rules that point at things that do not exist.

Set ``AGENTS_MD_PATH`` to run these checks against a different copy of the file.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PATH_PREFIXES = (
    "scripts/",
    "engine/",
    "docs/",
    "data/",
    "configs/",
    "backend/",
    "tests/",
    "formulas/",
)
PLACEHOLDERS = ("<", "*", "xxx", "...")


def _agents_md_text(path: str | os.PathLike[str] | None = None) -> str:
    chosen = path or os.environ.get("AGENTS_MD_PATH") or REPO_ROOT / "AGENTS.md"
    return Path(chosen).read_text(encoding="utf-8")


def _backticked_repo_paths(text: str) -> list[str]:
    found = []
    for token in re.findall(r"`([^`\n]+)`", text):
        token = token.strip()
        if not token.startswith(PATH_PREFIXES) or " " in token:
            continue
        if any(mark in token for mark in PLACEHOLDERS):
            continue
        found.append(token)
    return sorted(set(found))


def _path_exists(token: str) -> bool:
    """Accept ``path:LINE`` and ``module.function()`` references to existing files."""
    token = re.sub(r":\d+$", "", token).removesuffix("()")
    candidates = [token, f"{token}.py", f"{token.rsplit('.', 1)[0]}.py"]
    return any((REPO_ROOT / c).exists() for c in candidates)


def test_backticked_repo_paths_exist() -> None:
    missing = [
        p for p in _backticked_repo_paths(_agents_md_text()) if not _path_exists(p)
    ]
    assert not missing, f"AGENTS.md names paths that do not exist: {missing}"


def test_rule_numbers_are_unique() -> None:
    numbers = re.findall(r"\*\*.{0,4}RULE (\d+):", _agents_md_text())
    assert numbers, "no 'RULE n:' headings found"
    duplicates = sorted(n for n, count in Counter(numbers).items() if count > 1)
    assert not duplicates, f"RULE numbers used more than once: {duplicates}"


def test_no_grepp_command() -> None:
    assert "grepp" not in _agents_md_text()
