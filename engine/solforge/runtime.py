"""Public SolForge route gated by the admitted complexity registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.perception.complexity_registry import load_current_complexity_registry
from engine.solforge.contracts import (
    ExecutionReceiptV1,
    SolForgeCaseV1,
    SolHypothesisSetV1,
)
from engine.solforge.orchestrator import SolForgeRunState, run_solforge_shadow

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ComplexityRuntimeAdmissionError(RuntimeError):
    """The frozen admission chain or its executable source binding failed."""


@dataclass(frozen=True, slots=True)
class AdmittedSolForgeRun:
    registry_sha256: str
    admitted_module_ids: tuple[str, ...]
    state: SolForgeRunState


def run_admitted_solforge(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    *,
    execution: ExecutionReceiptV1 | None = None,
    project_root: Path | None = None,
) -> AdmittedSolForgeRun:
    """Run SolForge only after exact V5 admission and source-hash verification."""

    root = (project_root or _PROJECT_ROOT).resolve()
    try:
        registry = load_current_complexity_registry(root)
    except (OSError, ValueError) as exc:
        raise ComplexityRuntimeAdmissionError(
            f"COMPLEXITY_RUNTIME_GATE_FAILED: {exc}"
        ) from exc
    admitted = tuple(
        item.module_id for item in registry.modules if item.runtime_eligible
    )
    state = run_solforge_shadow(case, hypotheses, execution=execution)
    return AdmittedSolForgeRun(
        registry_sha256=registry.registry_sha256,
        admitted_module_ids=admitted,
        state=state,
    )


__all__ = [
    "AdmittedSolForgeRun",
    "ComplexityRuntimeAdmissionError",
    "run_admitted_solforge",
]
