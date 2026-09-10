"""Deterministic shadow-only SolForge orchestration state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from engine.evidence.augmentation import (
    DecisionDeltaV1,
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
)
from engine.solforge.adapters import (
    analyze_execution_receipt,
    build_criterion_fit_packet,
    build_temporal_packet,
    compile_architectural_delta,
    export_backend_lab_payloads,
)
from engine.solforge.contracts import (
    CompilationState,
    CompiledExperimentV1,
    CriterionFitPacketV1,
    DecisionReceiptV1,
    DecisionState,
    ExecutionReceiptV1,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    TemporalEvidencePacketV1,
)
from engine.solforge.governance import (
    GateFoundationPreflight,
    verify_gate_foundation_receipt,
)
from engine.solforge.hypotheses import validate_hypothesis_set

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SolForgeStage(str, Enum):
    INTAKE = "INTAKE"
    INVENTORY_REFRESHED = "INVENTORY_REFRESHED"
    HYPOTHESES_VALIDATED = "HYPOTHESES_VALIDATED"
    COMPILED = "COMPILED"
    EXPORTED = "EXPORTED"
    EVIDENCE_ANALYZED = "EVIDENCE_ANALYZED"
    DECIDED = "DECIDED"
    HELD = "HELD"


@dataclass(frozen=True, slots=True)
class SolForgeRunState:
    stage: SolForgeStage
    history: tuple[SolForgeStage, ...]
    gate_preflight: GateFoundationPreflight
    compiled_experiment: CompiledExperimentV1 | None
    backend_export: dict[str, Any] | None
    temporal_evidence: TemporalEvidencePacketV1 | None
    criterion_fit: CriterionFitPacketV1 | None
    decision_receipt: DecisionReceiptV1
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SolFacingEvidenceRoute:
    """Minimal structured route for one immutable augmentation receipt."""

    receipt_sha256: str
    state: EvidenceAugmentationState
    decision_delta: DecisionDeltaV1 | None
    advisory_text: tuple[str, ...]
    blockers: tuple[str, ...]
    forbidden_inference_codes: tuple[str, ...]


def route_evidence_delta(receipt: EvidenceDeltaReceiptV1) -> SolFacingEvidenceRoute:
    """Preserve every receipt while forwarding only an AUGMENT decision delta."""

    if not isinstance(receipt, EvidenceDeltaReceiptV1):
        raise TypeError("receipt must be an EvidenceDeltaReceiptV1")
    is_augment = receipt.state is EvidenceAugmentationState.AUGMENT
    is_hold = receipt.state is EvidenceAugmentationState.HOLD
    return SolFacingEvidenceRoute(
        receipt_sha256=receipt.receipt_sha256,
        state=receipt.state,
        decision_delta=receipt.delta if is_augment else None,
        advisory_text=(),
        blockers=receipt.blockers if is_hold else (),
        forbidden_inference_codes=(
            tuple(code for code in receipt.reason_codes if code.startswith("FORBID_"))
            if is_hold
            else ()
        ),
    )


def _decision(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    decision: DecisionState,
    *,
    compiled: CompiledExperimentV1 | None = None,
    execution: ExecutionReceiptV1 | None = None,
    temporal: TemporalEvidencePacketV1 | None = None,
    fit: CriterionFitPacketV1 | None = None,
    limitations: tuple[str, ...] = (),
    next_action: str | None = None,
) -> DecisionReceiptV1:
    return DecisionReceiptV1(
        case_sha256=case.record_sha256,
        hypothesis_set_sha256=hypotheses.record_sha256,
        compiled_experiment_sha256=(
            compiled.record_sha256 if compiled is not None else None
        ),
        execution_receipt_sha256=(
            execution.record_sha256 if execution is not None else None
        ),
        temporal_evidence_sha256=(
            temporal.record_sha256 if temporal is not None else None
        ),
        criterion_fit_sha256=fit.record_sha256 if fit is not None else None,
        decision=decision,
        evidence_limitations=limitations,
        next_action=next_action,
    )


def _held(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    preflight: GateFoundationPreflight,
    history: tuple[SolForgeStage, ...],
    blockers: tuple[str, ...],
    *,
    compiled: CompiledExperimentV1 | None = None,
    backend_export: dict[str, Any] | None = None,
    execution: ExecutionReceiptV1 | None = None,
    temporal: TemporalEvidencePacketV1 | None = None,
) -> SolForgeRunState:
    receipt = _decision(
        case,
        hypotheses,
        DecisionState.HOLD,
        compiled=compiled,
        execution=execution,
        temporal=temporal,
        limitations=blockers,
        next_action="Resolve every blocker before continuing the shadow loop.",
    )
    return SolForgeRunState(
        stage=SolForgeStage.HELD,
        history=(*history, SolForgeStage.HELD),
        gate_preflight=preflight,
        compiled_experiment=compiled,
        backend_export=backend_export,
        temporal_evidence=temporal,
        criterion_fit=None,
        decision_receipt=receipt,
        blockers=blockers,
    )


def _fit_decision(fit: CriterionFitPacketV1) -> DecisionState:
    if fit.validation_state != "VALIDATED_EXACT_SCOPE":
        return DecisionState.EVIDENCE_INSUFFICIENT
    intervals = fit.as_dict()["utility_intervals"]
    if not isinstance(intervals, dict) or "CONTROL" not in intervals:
        return DecisionState.EVIDENCE_INSUFFICIENT
    control = intervals["CONTROL"]
    control_midpoint = (float(control[0]) + float(control[1])) / 2
    intervention_midpoints = [
        (float(interval[0]) + float(interval[1])) / 2
        for item, interval in intervals.items()
        if item != "CONTROL"
    ]
    if not intervention_midpoints:
        return DecisionState.EVIDENCE_INSUFFICIENT
    return (
        DecisionState.TEST_NEXT
        if max(intervention_midpoints) > control_midpoint
        else DecisionState.RETAIN_CURRENT
    )


def run_solforge_shadow(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    *,
    execution: ExecutionReceiptV1 | None = None,
) -> SolForgeRunState:
    """Run one immutable shadow loop without external writes or live model calls."""

    preflight = verify_gate_foundation_receipt(_PROJECT_ROOT)
    history = (SolForgeStage.INTAKE,)
    if not preflight.ready:
        return _held(case, hypotheses, preflight, history, preflight.blockers)

    compiled = compile_architectural_delta(case, hypotheses)
    history = (*history, SolForgeStage.INVENTORY_REFRESHED)
    validation = validate_hypothesis_set(case, hypotheses)
    if not validation.valid:
        return _held(
            case,
            hypotheses,
            preflight,
            history,
            validation.blocker_codes,
            compiled=compiled,
        )
    history = (*history, SolForgeStage.HYPOTHESES_VALIDATED)
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
        receipt = _decision(
            case,
            hypotheses,
            DecisionState.NO_CHANGE,
            compiled=compiled,
            limitations=("No nonredundant target-faithful delta was justified.",),
            next_action="Retain the current target architecture.",
        )
        return SolForgeRunState(
            stage=SolForgeStage.DECIDED,
            history=(*history, SolForgeStage.DECIDED),
            gate_preflight=preflight,
            compiled_experiment=compiled,
            backend_export=None,
            temporal_evidence=None,
            criterion_fit=None,
            decision_receipt=receipt,
            blockers=(),
        )

    history = (*history, SolForgeStage.COMPILED)
    backend_export = export_backend_lab_payloads(compiled)
    history = (*history, SolForgeStage.EXPORTED)
    if execution is None:
        receipt = _decision(
            case,
            hypotheses,
            DecisionState.EVIDENCE_INSUFFICIENT,
            compiled=compiled,
            limitations=("No execution receipt or observed evidence was supplied.",),
            next_action=compiled.next_comparison,
        )
        return SolForgeRunState(
            stage=SolForgeStage.EXPORTED,
            history=history,
            gate_preflight=preflight,
            compiled_experiment=compiled,
            backend_export=backend_export,
            temporal_evidence=None,
            criterion_fit=None,
            decision_receipt=receipt,
            blockers=(),
        )
    if execution.compiled_experiment_sha256 != compiled.record_sha256:
        return _held(
            case,
            hypotheses,
            preflight,
            history,
            ("EXECUTION_PARENT_MISMATCH",),
            compiled=compiled,
            backend_export=backend_export,
            execution=execution,
        )

    temporal_result = analyze_execution_receipt(execution)
    temporal = build_temporal_packet(execution, temporal_result)
    history = (*history, SolForgeStage.EVIDENCE_ANALYZED)
    if temporal.state == "HOLD" or temporal.safety_stop:
        return _held(
            case,
            hypotheses,
            preflight,
            history,
            ("TEMPORAL_EVIDENCE_HELD",),
            compiled=compiled,
            backend_export=backend_export,
            execution=execution,
            temporal=temporal,
        )
    fit = build_criterion_fit_packet(
        execution,
        temporal,
        criterion=case.criterion,
    )
    decision = _fit_decision(fit)
    receipt = _decision(
        case,
        hypotheses,
        decision,
        compiled=compiled,
        execution=execution,
        temporal=temporal,
        fit=fit,
        limitations=(
            "This is a scoped shadow decision and grants no physical or release authority.",
        ),
        next_action=(
            "Run the next discriminating blinded comparison."
            if decision is DecisionState.TEST_NEXT
            else "Retain current design pending stronger exact-scope evidence."
        ),
    )
    return SolForgeRunState(
        stage=SolForgeStage.DECIDED,
        history=(*history, SolForgeStage.DECIDED),
        gate_preflight=preflight,
        compiled_experiment=compiled,
        backend_export=backend_export,
        temporal_evidence=temporal,
        criterion_fit=fit,
        decision_receipt=receipt,
        blockers=(),
    )


__all__ = [
    "SolFacingEvidenceRoute",
    "SolForgeRunState",
    "SolForgeStage",
    "route_evidence_delta",
    "run_solforge_shadow",
]
