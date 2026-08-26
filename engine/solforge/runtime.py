"""Public SolForge route gated to the admitted Architectural Delta engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from engine.perception.complexity_registry import (
    ComplexityRegistry,
    load_current_complexity_registry,
)
from engine.solforge.architectural_adapter import (
    compile_architectural_delta,
    export_backend_lab_payloads,
)
from engine.solforge.contracts import (
    CompilationState,
    CompiledExperimentV1,
    DecisionReceiptV1,
    DecisionState,
    ExecutionReceiptV1,
    SolForgeCaseV1,
    SolHypothesisSetV1,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ComplexityRuntimeAdmissionError(RuntimeError):
    """The frozen admission chain or its executable source binding failed."""


class ArchitecturalRuntimeStage(str, Enum):
    INTAKE = "INTAKE"
    COMPILED = "COMPILED"
    EXPORTED = "EXPORTED"
    DECIDED = "DECIDED"
    HELD = "HELD"


@dataclass(frozen=True, slots=True)
class ComplexityRuntimePreflight:
    """Exact-registry readiness without retired evidence-gate dependencies."""

    ready: bool
    registry_sha256: str | None
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitecturalRuntimeState:
    stage: ArchitecturalRuntimeStage
    history: tuple[ArchitecturalRuntimeStage, ...]
    gate_preflight: ComplexityRuntimePreflight
    compiled_experiment: CompiledExperimentV1 | None
    backend_export: dict[str, Any] | None
    temporal_evidence: None
    criterion_fit: None
    decision_receipt: DecisionReceiptV1
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdmittedSolForgeRun:
    registry_sha256: str
    admitted_module_ids: tuple[str, ...]
    state: ArchitecturalRuntimeState


def _decision(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    decision: DecisionState,
    *,
    compiled: CompiledExperimentV1 | None = None,
    limitations: tuple[str, ...] = (),
    next_action: str | None = None,
) -> DecisionReceiptV1:
    return DecisionReceiptV1(
        case_sha256=case.record_sha256,
        hypothesis_set_sha256=hypotheses.record_sha256,
        compiled_experiment_sha256=(
            compiled.record_sha256 if compiled is not None else None
        ),
        execution_receipt_sha256=None,
        temporal_evidence_sha256=None,
        criterion_fit_sha256=None,
        decision=decision,
        evidence_limitations=limitations,
        next_action=next_action,
    )


def _held(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    preflight: ComplexityRuntimePreflight,
    history: tuple[ArchitecturalRuntimeStage, ...],
    blockers: tuple[str, ...],
    *,
    compiled: CompiledExperimentV1 | None = None,
    backend_export: dict[str, Any] | None = None,
) -> ArchitecturalRuntimeState:
    return ArchitecturalRuntimeState(
        stage=ArchitecturalRuntimeStage.HELD,
        history=(*history, ArchitecturalRuntimeStage.HELD),
        gate_preflight=preflight,
        compiled_experiment=compiled,
        backend_export=backend_export,
        temporal_evidence=None,
        criterion_fit=None,
        decision_receipt=_decision(
            case,
            hypotheses,
            DecisionState.HOLD,
            compiled=compiled,
            limitations=blockers,
            next_action="Resolve every blocker before continuing.",
        ),
        blockers=blockers,
    )


def _verify_complexity_runtime(project_root: Path) -> tuple[
    ComplexityRuntimePreflight,
    ComplexityRegistry | None,
]:
    try:
        registry = load_current_complexity_registry(project_root.resolve())
    except (OSError, ValueError) as exc:
        return (
            ComplexityRuntimePreflight(
                ready=False,
                registry_sha256=None,
                blockers=(f"COMPLEXITY_RUNTIME_GATE_FAILED: {exc}",),
            ),
            None,
        )
    return (
        ComplexityRuntimePreflight(
            ready=True,
            registry_sha256=registry.registry_sha256,
            blockers=(),
        ),
        registry,
    )


def _run_architectural_runtime(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    *,
    execution: ExecutionReceiptV1 | None,
    preflight: ComplexityRuntimePreflight,
) -> ArchitecturalRuntimeState:
    history = (ArchitecturalRuntimeStage.INTAKE,)
    if not preflight.ready:
        return _held(case, hypotheses, preflight, history, preflight.blockers)

    compiled = compile_architectural_delta(case, hypotheses)
    if compiled.state is CompilationState.HOLD:
        return _held(
            case,
            hypotheses,
            preflight,
            history,
            compiled.blockers,
            compiled=compiled,
        )
    if compiled.state is CompilationState.NO_CHANGE:
        return ArchitecturalRuntimeState(
            stage=ArchitecturalRuntimeStage.DECIDED,
            history=(*history, ArchitecturalRuntimeStage.DECIDED),
            gate_preflight=preflight,
            compiled_experiment=compiled,
            backend_export=None,
            temporal_evidence=None,
            criterion_fit=None,
            decision_receipt=_decision(
                case,
                hypotheses,
                DecisionState.NO_CHANGE,
                compiled=compiled,
                limitations=(
                    "No nonredundant target-faithful delta was justified.",
                ),
                next_action="Retain the current target architecture.",
            ),
            blockers=(),
        )

    history = (*history, ArchitecturalRuntimeStage.COMPILED)
    backend_export = export_backend_lab_payloads(compiled)
    history = (*history, ArchitecturalRuntimeStage.EXPORTED)
    if execution is not None:
        return _held(
            case,
            hypotheses,
            preflight,
            history,
            ("EVIDENCE_ANALYSIS_MODULE_NOT_ADMITTED",),
            compiled=compiled,
            backend_export=backend_export,
        )
    return ArchitecturalRuntimeState(
        stage=ArchitecturalRuntimeStage.EXPORTED,
        history=history,
        gate_preflight=preflight,
        compiled_experiment=compiled,
        backend_export=backend_export,
        temporal_evidence=None,
        criterion_fit=None,
        decision_receipt=_decision(
            case,
            hypotheses,
            DecisionState.EVIDENCE_INSUFFICIENT,
            compiled=compiled,
            limitations=(
                "No admitted temporal or preference evidence analyzer is available.",
            ),
            next_action=compiled.next_comparison,
        ),
        blockers=(),
    )


def run_solforge_shadow(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    *,
    execution: ExecutionReceiptV1 | None = None,
) -> ArchitecturalRuntimeState:
    """Run only the admitted experiment compiler; evidence learners stay unreachable."""

    preflight, _ = _verify_complexity_runtime(_PROJECT_ROOT)
    return _run_architectural_runtime(
        case,
        hypotheses,
        execution=execution,
        preflight=preflight,
    )


def run_admitted_solforge(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    *,
    execution: ExecutionReceiptV1 | None = None,
    project_root: Path | None = None,
) -> AdmittedSolForgeRun:
    """Run SolForge only after exact current-registry verification."""

    root = (project_root or _PROJECT_ROOT).resolve()
    preflight, registry = _verify_complexity_runtime(root)
    if registry is None:
        raise ComplexityRuntimeAdmissionError(
            "; ".join(preflight.blockers)
        )
    admitted = tuple(
        item.module_id for item in registry.modules if item.runtime_eligible
    )
    return AdmittedSolForgeRun(
        registry_sha256=registry.registry_sha256,
        admitted_module_ids=admitted,
        state=_run_architectural_runtime(
            case,
            hypotheses,
            execution=execution,
            preflight=preflight,
        ),
    )


__all__ = [
    "AdmittedSolForgeRun",
    "ArchitecturalRuntimeStage",
    "ArchitecturalRuntimeState",
    "ComplexityRuntimePreflight",
    "ComplexityRuntimeAdmissionError",
    "run_admitted_solforge",
    "run_solforge_shadow",
]
