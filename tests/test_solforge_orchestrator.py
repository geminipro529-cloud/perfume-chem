from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence.augmentation import (
    DecisionDeltaV1,
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
    hold_receipt,
    no_augmentation_receipt,
)
from engine.solforge.contracts import (
    CompilationState,
    CompiledArmV1,
    CompiledExperimentV1,
    CriterionFitPacketV1,
    DecisionState,
    ExecutionReceiptV1,
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    TemporalEvidencePacketV1,
)
from engine.solforge.governance import GateFoundationPreflight
from engine.solforge.orchestrator import (
    SolForgeStage,
    route_evidence_delta,
    run_solforge_shadow,
)

H = "a" * 64


def _case() -> SolForgeCaseV1:
    return SolForgeCaseV1(
        case_id="C1", state=SolForgeCaseState.READY, target_identity="precise iris",
        ideal_architecture={"heart": ["iris"]}, current_inventory_build={"materials": {}},
        inventory_path="inventory.xlsx", inventory_sha256=H, formula_sha256="b" * 64,
        dose_receipt_sha256="c" * 64, constraints=("constant total",),
        criterion="DEPTH", forbidden_claims=("release",),
    )


def _hypotheses(case: SolForgeCaseV1) -> SolHypothesisSetV1:
    return SolHypothesisSetV1(
        case_sha256=case.record_sha256, model_identity="Sol", reasoning_setting="xhigh",
        prompt_sha256=H, input_sha256="b" * 64, output_sha256="c" * 64,
        hypotheses=(), uncertainty="untested",
    )


def _compiled(case, hypotheses, state=CompilationState.COMPILED):
    arms = () if state is not CompilationState.COMPILED else (
        CompiledArmV1("CONTROL", {"factor": False}, 1.0, "B1", "d" * 64),
        CompiledArmV1("TREATMENT", {"factor": True}, 1.0, "B2", "e" * 64),
    )
    return CompiledExperimentV1(
        case_sha256=case.record_sha256, hypothesis_set_sha256=hypotheses.record_sha256,
        inventory_refresh_sha256=H, inventory_source_row_count=190, state=state,
        delta_kind="ADDITION" if arms else None,
        selected_hypothesis_id="H1" if arms else None, arms=arms,
        blockers=("blocked",) if state is CompilationState.HOLD else (),
        inventory_statuses=(), omission_loss=None, failure_mode=None,
        next_comparison="compare" if arms else None,
    )


def _execution(compiled: CompiledExperimentV1) -> ExecutionReceiptV1:
    return ExecutionReceiptV1(
        compiled_experiment_sha256=compiled.record_sha256,
        executor="SYNTHETIC_FIXTURE", execution_context={"fixture": True, "synthetic": True},
        sample_sha256=(("CONTROL", "d" * 64), ("TREATMENT", "e" * 64)),
        deviations=(), test_only=True,
    )


@pytest.fixture(autouse=True)
def _ready_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "engine.solforge.orchestrator.verify_gate_foundation_receipt",
        lambda *_: GateFoundationPreflight(True, H, ()),
    )


def test_missing_execution_stops_at_export_with_evidence_insufficient(monkeypatch) -> None:
    case = _case()
    hypotheses = _hypotheses(case)
    compiled = _compiled(case, hypotheses)
    monkeypatch.setattr("engine.solforge.orchestrator.compile_architectural_delta", lambda *_: compiled)
    monkeypatch.setattr("engine.solforge.orchestrator.validate_hypothesis_set", lambda *_: type("V", (), {"valid": True, "no_change": False, "blocker_codes": ()})())
    monkeypatch.setattr("engine.solforge.orchestrator.export_backend_lab_payloads", lambda *_: {"draft": True})
    result = run_solforge_shadow(case, hypotheses)
    assert result.stage is SolForgeStage.EXPORTED
    assert result.history == (
        SolForgeStage.INTAKE, SolForgeStage.INVENTORY_REFRESHED,
        SolForgeStage.HYPOTHESES_VALIDATED, SolForgeStage.COMPILED,
        SolForgeStage.EXPORTED,
    )
    assert result.decision_receipt.decision is DecisionState.EVIDENCE_INSUFFICIENT


def test_no_change_goes_directly_to_decided_after_inventory_lineage(monkeypatch) -> None:
    case = _case()
    hypotheses = _hypotheses(case)
    compiled = _compiled(case, hypotheses, CompilationState.NO_CHANGE)
    monkeypatch.setattr("engine.solforge.orchestrator.compile_architectural_delta", lambda *_: compiled)
    monkeypatch.setattr("engine.solforge.orchestrator.validate_hypothesis_set", lambda *_: type("V", (), {"valid": True, "no_change": True, "blocker_codes": ()})())
    result = run_solforge_shadow(case, hypotheses)
    assert result.stage is SolForgeStage.DECIDED
    assert SolForgeStage.COMPILED not in result.history
    assert result.decision_receipt.decision is DecisionState.NO_CHANGE
    assert result.compiled_experiment.inventory_source_row_count == 190


def test_any_validation_or_compilation_blocker_moves_to_held(monkeypatch) -> None:
    case = _case()
    hypotheses = _hypotheses(case)
    monkeypatch.setattr(
        "engine.solforge.orchestrator.compile_architectural_delta",
        lambda *_: _compiled(case, hypotheses, CompilationState.HOLD),
    )
    monkeypatch.setattr("engine.solforge.orchestrator.validate_hypothesis_set", lambda *_: type("V", (), {"valid": False, "no_change": False, "blocker_codes": ("BAD",)})())
    result = run_solforge_shadow(case, hypotheses)
    assert result.stage is SolForgeStage.HELD
    assert result.blockers == ("BAD",)
    assert result.decision_receipt.decision is DecisionState.HOLD


def test_execution_parent_mismatch_is_held(monkeypatch) -> None:
    case = _case()
    hypotheses = _hypotheses(case)
    compiled = _compiled(case, hypotheses)
    execution = replace(_execution(compiled), compiled_experiment_sha256="f" * 64)
    monkeypatch.setattr("engine.solforge.orchestrator.compile_architectural_delta", lambda *_: compiled)
    monkeypatch.setattr("engine.solforge.orchestrator.validate_hypothesis_set", lambda *_: type("V", (), {"valid": True, "no_change": False, "blocker_codes": ()})())
    monkeypatch.setattr("engine.solforge.orchestrator.export_backend_lab_payloads", lambda *_: {"draft": True})
    result = run_solforge_shadow(case, hypotheses, execution=execution)
    assert result.stage is SolForgeStage.HELD
    assert "EXECUTION_PARENT_MISMATCH" in result.blockers


def test_full_path_is_deterministic_and_hash_binds_descendants(monkeypatch) -> None:
    case = _case()
    hypotheses = _hypotheses(case)
    compiled = _compiled(case, hypotheses)
    execution = _execution(compiled)
    temporal = TemporalEvidencePacketV1(
        execution_receipt_sha256=execution.record_sha256, ledger_payload_sha256="f" * 64,
        state="COMPLETE", observed_cell_count=4, missing_cells=(), duplicate_cells=(),
        disagreement={}, safety_stop=False, next_discriminator="repeat", test_only=True,
    )
    fit = CriterionFitPacketV1(
        temporal_evidence_sha256=temporal.record_sha256,
        comparison_payload_sha256=H, criterion="DEPTH", preference_result_sha256="b" * 64,
        validation_state="VALIDATED_EXACT_SCOPE",
        utility_intervals={"CONTROL": [-1.0, 0.0], "TREATMENT": [0.1, 1.0]},
        tie_rate=0, assessor_heterogeneity=0.1, order_effect=0,
        next_pair=("CONTROL", "TREATMENT"), test_only=True,
    )
    monkeypatch.setattr("engine.solforge.orchestrator.compile_architectural_delta", lambda *_: compiled)
    monkeypatch.setattr("engine.solforge.orchestrator.validate_hypothesis_set", lambda *_: type("V", (), {"valid": True, "no_change": False, "blocker_codes": ()})())
    monkeypatch.setattr("engine.solforge.orchestrator.export_backend_lab_payloads", lambda *_: {"draft": True})
    monkeypatch.setattr("engine.solforge.orchestrator.analyze_execution_receipt", lambda *_: object())
    monkeypatch.setattr("engine.solforge.orchestrator.build_temporal_packet", lambda *_: temporal)
    monkeypatch.setattr("engine.solforge.orchestrator.build_criterion_fit_packet", lambda *_args, **_kwargs: fit)
    first = run_solforge_shadow(case, hypotheses, execution=execution)
    second = run_solforge_shadow(case, hypotheses, execution=execution)
    assert first.decision_receipt.canonical_bytes() == second.decision_receipt.canonical_bytes()
    assert first.history[-2:] == (SolForgeStage.EVIDENCE_ANALYZED, SolForgeStage.DECIDED)
    assert first.decision_receipt.decision is DecisionState.TEST_NEXT

    changed_fit = replace(fit, preference_result_sha256="c" * 64)
    monkeypatch.setattr("engine.solforge.orchestrator.build_criterion_fit_packet", lambda *_args, **_kwargs: changed_fit)
    changed = run_solforge_shadow(case, hypotheses, execution=execution)
    assert changed.decision_receipt.record_sha256 != first.decision_receipt.record_sha256


def test_no_augmentation_routes_no_prose_but_preserves_receipt_hash() -> None:
    receipt = no_augmentation_receipt(
        module_id="architectural_delta",
        exact_scope="case/target",
        input_sha256=H,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("QUESTION_ALREADY_RESOLVED",),
    )
    route = route_evidence_delta(receipt)
    assert route.receipt_sha256 == receipt.receipt_sha256
    assert route.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert route.decision_delta is None
    assert route.advisory_text == ()
    assert route.blockers == ()


def test_only_augment_forwards_the_structured_decision_delta() -> None:
    delta = DecisionDeltaV1(
        delta_id="D1",
        decision_effect="Run one isolated constant-total comparison.",
        observed_facts=("target gap is documented",),
        derived_calculations=(),
        hypotheses=("candidate may close the gap",),
        forbidden_inferences=("No sensory success is established.",),
    )
    receipt = EvidenceDeltaReceiptV1(
        module_id="architectural_delta",
        exact_scope="case/target",
        state=EvidenceAugmentationState.AUGMENT,
        input_sha256=H,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        source_binding_sha256=("d" * 64,),
        reason_codes=("NONREDUNDANT_EXPERIMENT",),
        delta=delta,
        blockers=(),
        next_action="COMPARE:CONTROL:TREATMENT",
    )
    route = route_evidence_delta(receipt)
    assert route.decision_delta is delta
    assert route.advisory_text == ()
    assert route.blockers == ()
    assert route.forbidden_inference_codes == ()


def test_hold_forwards_only_blockers_and_stable_inference_codes() -> None:
    receipt = hold_receipt(
        module_id="temporal_ledger",
        exact_scope="protocol/sample",
        input_sha256=H,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("FORBID_INTERPOLATION", "MISSING_CELL"),
        blockers=("one canonical observation cell is missing",),
        next_action="OBSERVE:MISSING_CELL",
    )
    route = route_evidence_delta(receipt)
    assert route.decision_delta is None
    assert route.advisory_text == ()
    assert route.blockers == receipt.blockers
    assert route.forbidden_inference_codes == ("FORBID_INTERPOLATION",)
