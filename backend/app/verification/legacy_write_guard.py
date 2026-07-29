"""Fail closed when backend code introduces a legacy dual-write path."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

LEGACY_LEDGER_IMPORTS = {
    "engine.analytical.ledger": {"AnalyticalLedger"},
    "engine.bottle.events": {"BottleBatch"},
    "engine.evidence.ledger": {"EvidenceLedger"},
    "engine.inventory.stock_model": {"InventoryLedger"},
    "engine.sensory.ledger": {"SensoryTrial"},
}

FORBIDDEN_ADAPTER_CALLS = {
    "add_claim",
    "add_event",
    "add_gcms_run",
    "add_gco_event",
    "add_hsspme_run",
    "add_sample",
    "add_source",
    "add_stock",
    "consume",
    "record_observation",
    "remove_stock",
}

FORBIDDEN_ADAPTER_IMPORTS = {
    ("sqlalchemy.ext.asyncio", "AsyncSession"),
    ("app.repositories.lab", "LabRepository"),
    ("app.services.lab_service", "LabService"),
}


@dataclass(frozen=True, slots=True)
class LegacyWriteViolation:
    """One source location that can create a duplicate legacy write."""

    path: str
    line: int
    code: str
    detail: str


def scan_legacy_write_paths(app_root: Path) -> tuple[LegacyWriteViolation, ...]:
    """Parse backend application sources and return deterministic violations."""
    root = app_root.resolve()
    violations: list[LegacyWriteViolation] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(root).as_posix()
        is_adapter = relative.startswith("adapters/")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {alias.name for alias in node.names}
                if not is_adapter:
                    prohibited = names & LEGACY_LEDGER_IMPORTS.get(node.module or "", set())
                    for name in sorted(prohibited):
                        violations.append(
                            LegacyWriteViolation(
                                relative,
                                node.lineno,
                                "LEGACY_LEDGER_IMPORT",
                                f"{node.module}.{name}",
                            )
                        )
                else:
                    for module, name in FORBIDDEN_ADAPTER_IMPORTS:
                        if node.module == module and name in names:
                            violations.append(
                                LegacyWriteViolation(
                                    relative,
                                    node.lineno,
                                    "ADAPTER_TRANSACTION_AUTHORITY",
                                    f"{module}.{name}",
                                )
                            )
            elif (
                is_adapter
                and isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in FORBIDDEN_ADAPTER_CALLS
            ):
                violations.append(
                    LegacyWriteViolation(
                        relative,
                        node.lineno,
                        "ADAPTER_LEGACY_MUTATION",
                        node.func.attr,
                    )
                )
            elif (
                is_adapter
                and isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"commit", "rollback"}
            ):
                violations.append(
                    LegacyWriteViolation(
                        relative,
                        node.lineno,
                        "ADAPTER_TRANSACTION_CALL",
                        node.func.attr,
                    )
                )
    return tuple(
        sorted(
            violations,
            key=lambda violation: (
                violation.path,
                violation.line,
                violation.code,
                violation.detail,
            ),
        )
    )


def assert_no_legacy_write_paths(app_root: Path) -> None:
    """Raise with stable diagnostics when a prohibited path is present."""
    violations = scan_legacy_write_paths(app_root)
    if not violations:
        return
    details = "\n".join(
        f"{item.path}:{item.line}: {item.code}: {item.detail}"
        for item in violations
    )
    raise RuntimeError(f"legacy dual-write guard failed:\n{details}")


__all__ = [
    "LegacyWriteViolation",
    "assert_no_legacy_write_paths",
    "scan_legacy_write_paths",
]
