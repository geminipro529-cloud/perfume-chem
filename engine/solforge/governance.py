"""Fail-closed governance checks for SolForge predecessor receipts."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.solforge.gate_foundation import (
    ACCEPTANCE_AUTHORITY_FLAGS,
    validate_gate_foundation_receipt,
)

GATE_FOUNDATION_RECEIPT_PATH = Path(
    "data/governance/solforge_gate_foundation_acceptance_v2.json"
)


@dataclass(frozen=True, slots=True)
class GateFoundationReceipt:
    """Minimum trusted view of a validated Gate Foundation receipt."""

    acceptance_sha256: str
    repository_commit: str
    file_sha256: tuple[tuple[str, str], ...]
    check_count: int
    authority_flags: tuple[tuple[str, bool], ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GateFoundationReceipt:
        core = payload["acceptance_core"]
        return cls(
            acceptance_sha256=str(payload["acceptance_sha256"]),
            repository_commit=str(core["repository_commit"]),
            file_sha256=tuple(sorted(core["file_sha256"].items())),
            check_count=len(core["checks"]),
            authority_flags=tuple(sorted(core["authority_flags"].items())),
        )


@dataclass(frozen=True, slots=True)
class GateFoundationPreflight:
    """Non-mutating readiness result for the SolForge predecessor."""

    ready: bool
    acceptance_sha256: str | None
    blockers: tuple[str, ...]
    receipt: GateFoundationReceipt | None = None


def _commit_is_ancestor(project_root: Path, commit: str) -> bool:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        return False
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=project_root,
        capture_output=True,
        check=False,
        timeout=10,
    )
    return result.returncode == 0


def verify_gate_foundation_receipt(project_root: Path) -> GateFoundationPreflight:
    """Validate exact receipt bytes, recorded files, checks, and Git ancestry."""

    project_root = Path(project_root).resolve()
    path = project_root / GATE_FOUNDATION_RECEIPT_PATH
    if not path.is_file():
        return GateFoundationPreflight(False, None, ("Gate Foundation receipt is missing",))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return GateFoundationPreflight(
            False, None, ("Gate Foundation receipt is malformed JSON",)
        )

    blockers = list(validate_gate_foundation_receipt(project_root, payload))
    receipt: GateFoundationReceipt | None = None
    acceptance_sha256 = payload.get("acceptance_sha256") if isinstance(payload, dict) else None
    try:
        receipt = GateFoundationReceipt.from_dict(payload)
    except (KeyError, TypeError, ValueError, AttributeError):
        if "receipt or acceptance_core is malformed" not in blockers:
            blockers.append("receipt or acceptance_core is malformed")
    if receipt is not None:
        if receipt.authority_flags != tuple(sorted(ACCEPTANCE_AUTHORITY_FLAGS.items())):
            blocker = "authority flags are not the required all-false mapping"
            if blocker not in blockers:
                blockers.append(blocker)
        if not _commit_is_ancestor(project_root, receipt.repository_commit):
            blockers.append("receipt commit is not an ancestor of HEAD")

    return GateFoundationPreflight(
        ready=not blockers,
        acceptance_sha256=(
            str(acceptance_sha256) if isinstance(acceptance_sha256, str) else None
        ),
        blockers=tuple(blockers),
        receipt=receipt if not blockers else None,
    )


__all__ = [
    "GATE_FOUNDATION_RECEIPT_PATH",
    "GateFoundationPreflight",
    "GateFoundationReceipt",
    "verify_gate_foundation_receipt",
]
