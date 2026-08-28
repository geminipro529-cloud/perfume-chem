from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence.augmentation import (
    DecisionDeltaV1,
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
    no_augmentation_receipt,
)
from engine.evidence_contracts import sha256_hex
from engine.solforge.contracts import (
    AUTHORITY_FLAGS_FALSE,
    CompilationState,
    CompiledArmV1,
    CompiledExperimentV1,
    CriterionFitPacketV1,
    CriterionFitPacketV2,
    CriterionFitPacketV3,
    DecisionReceiptV1,
    DecisionState,
    EvidenceDeltaPacketV2,
    ExecutionReceiptV1,
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
    TemporalEvidencePacketV1,
)

H = "a" * 64
H2 = "b" * 64


def _records():
    case = SolForgeCaseV1(
        case_id="CASE-1",
        state=SolForgeCaseState.READY,
        target_identity="dry orange-blossom cologne",
        ideal_architecture={"top": ["bitter orange"], "heart": ["neroli support"]},
        current_inventory_build={"materials": [{"name": "Neroli EO 10%", "parts": 1}]},
        inventory_path="inventory-v5.xlsx",
        inventory_sha256=H,
        formula_sha256=H2,
        dose_receipt_sha256="c" * 64,
        constraints=("constant total",),
        criterion="DEPTH",
        forbidden_claims=("physical liking", "release"),
    )
    hypothesis = SolHypothesisV1(
        hypothesis_id="H1",
        rank=1,
        claim="Neroli can bridge the floral heart without becoming primary citrus.",
        target_function="heart bridge",
        material_names=("Neroli EO 10%",),
        intervention_kind="ADDITION",
        expected_behavior="longer floral-citrus continuity",
        rationale="target-functional relation",
        uncertainty=0.4,
        evidence_refs=(H,),
        nary_factors=(),
    )
    hypotheses = SolHypothesisSetV1(
        case_sha256=case.record_sha256,
        model_identity="Sol 5.6 xhigh",
        reasoning_setting="xhigh",
        prompt_sha256=H,
        input_sha256=H2,
        output_sha256="c" * 64,
        hypotheses=(hypothesis,),
        uncertainty="support role requires testing",
    )
    arm = CompiledArmV1(
        arm_id="CONTROL",
        formula={"Neroli EO 10%": 0.0, "carrier": 99.0},
        total_active_mass_g=1.0,
        blind_code="B17",
        sample_sha256="d" * 64,
    )
    experiment = CompiledExperimentV1(
        case_sha256=case.record_sha256,
        hypothesis_set_sha256=hypotheses.record_sha256,
        inventory_refresh_sha256=H,
        inventory_source_row_count=190,
        state=CompilationState.COMPILED,
        delta_kind="ADDITION",
        selected_hypothesis_id="H1",
        arms=(arm,),
        blockers=(),
        inventory_statuses=(("Neroli EO 10%", "OWNED"),),
        omission_loss="less continuity",
        failure_mode="orange-blossom takeover",
        next_comparison="control versus support",
    )
    execution = ExecutionReceiptV1(
        compiled_experiment_sha256=experiment.record_sha256,
        executor="SYNTHETIC_FIXTURE",
        execution_context={"protocol": "P1", "synthetic": True},
        sample_sha256=(("CONTROL", "d" * 64),),
        deviations=(),
        test_only=True,
    )
    temporal = TemporalEvidencePacketV1(
        execution_receipt_sha256=execution.record_sha256,
        ledger_payload_sha256="e" * 64,
        state="DIAGNOSTIC",
        observed_cell_count=12,
        missing_cells=(),
        duplicate_cells=(),
        disagreement={"depth": 0.2},
        safety_stop=False,
        next_discriminator="repeat heart at 2h",
        test_only=True,
    )
    fit = CriterionFitPacketV1(
        temporal_evidence_sha256=temporal.record_sha256,
        comparison_payload_sha256="f" * 64,
        criterion="DEPTH",
        preference_result_sha256=H,
        validation_state="DIAGNOSTIC",
        utility_intervals={"CONTROL": [-0.2, 0.2]},
        tie_rate=0.2,
        assessor_heterogeneity=0.3,
        order_effect=0.1,
        next_pair=("CONTROL", "TREATMENT"),
        test_only=True,
    )
    decision = DecisionReceiptV1(
        case_sha256=case.record_sha256,
        hypothesis_set_sha256=hypotheses.record_sha256,
        compiled_experiment_sha256=experiment.record_sha256,
        execution_receipt_sha256=execution.record_sha256,
        temporal_evidence_sha256=temporal.record_sha256,
        criterion_fit_sha256=fit.record_sha256,
        decision=DecisionState.EVIDENCE_INSUFFICIENT,
        evidence_limitations=("synthetic fixture",),
        next_action="run physical blinded comparison",
    )
    return case, hypothesis, hypotheses, arm, experiment, execution, temporal, fit, decision


@pytest.mark.parametrize("index", range(9))
def test_every_record_round_trips_with_identical_canonical_bytes(index: int) -> None:
    record = _records()[index]
    restored = type(record).from_dict(record.as_dict())
    assert restored.canonical_bytes() == record.canonical_bytes()
    assert restored.record_sha256 == sha256_hex(record.canonical_bytes())
    assert record.as_dict()["authority_flags"] == AUTHORITY_FLAGS_FALSE


@pytest.mark.parametrize("index", range(9))
def test_every_record_rejects_unknown_fields(index: int) -> None:
    record = _records()[index]
    payload = record.as_dict()
    payload["unknown"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        type(record).from_dict(payload)


def test_case_deep_freezes_ideal_and_inventory_build() -> None:
    ideal = {"layers": ["top"]}
    build = {"layers": ["heart"]}
    case = replace(_records()[0], ideal_architecture=ideal, current_inventory_build=build)
    ideal["layers"].append("base")
    build["layers"].append("base")
    assert case.as_dict()["ideal_architecture"] == {"layers": ["top"]}
    assert case.as_dict()["current_inventory_build"] == {"layers": ["heart"]}


def test_duplicate_hypothesis_and_arm_ids_are_rejected() -> None:
    _, hypothesis, hypotheses, arm, experiment, *_ = _records()
    with pytest.raises(ValueError, match="duplicate hypothesis_id"):
        replace(hypotheses, hypotheses=(hypothesis, hypothesis))
    with pytest.raises(ValueError, match="duplicate arm_id"):
        replace(experiment, arms=(arm, arm))


def test_invalid_sha_and_synthetic_execution_are_rejected() -> None:
    case = _records()[0]
    with pytest.raises(ValueError, match="SHA-256"):
        replace(case, inventory_sha256="A" * 64)
    execution = _records()[5]
    with pytest.raises(ValueError, match="test_only"):
        replace(execution, test_only=False)


def test_decision_receipt_hash_binds_every_parent() -> None:
    receipt = _records()[-1]
    assert receipt.record_sha256 == sha256_hex(receipt.canonical_bytes())
    changed = replace(receipt, criterion_fit_sha256="f" * 64)
    assert changed.record_sha256 != receipt.record_sha256


def test_closed_enum_and_schema_values_are_enforced() -> None:
    case = _records()[0]
    with pytest.raises(ValueError):
        replace(case, state="UNKNOWN")
    payload = case.as_dict()
    payload["schema_version"] = "future"
    with pytest.raises(ValueError, match="schema_version"):
        SolForgeCaseV1.from_dict(payload)


def test_v1_decision_bytes_remain_frozen_when_v2_transport_is_added() -> None:
    decision = _records()[-1]
    assert decision.record_sha256 == (
        "cc9cb0c34ddc872a2664ee2d7e40e65f277019912af6590391ee544bf1d9a00d"
    )
    payload = decision.as_dict()
    payload["evidence_delta_receipt"] = None
    with pytest.raises(ValueError, match="unknown fields"):
        DecisionReceiptV1.from_dict(payload)


def test_v2_transport_optionally_binds_one_evidence_delta_receipt() -> None:
    decision = _records()[-1]
    receipt = no_augmentation_receipt(
        module_id="temporal_sensory_ledger",
        exact_scope="P1/BLIND-A/DEPTH/60-1800s",
        input_sha256="a" * 64,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("QUESTION_ALREADY_RESOLVED",),
    )
    packet = EvidenceDeltaPacketV2(
        parent_decision=decision,
        evidence_delta_receipt=receipt,
    )
    assert EvidenceDeltaPacketV2.from_dict(packet.as_dict()) == packet
    empty = EvidenceDeltaPacketV2(
        parent_decision=decision,
        evidence_delta_receipt=None,
    )
    assert EvidenceDeltaPacketV2.from_dict(empty.as_dict()) == empty


def test_criterion_fit_v2_round_trips_with_proper_validation_hashes() -> None:
    parent = _records()[7]
    receipt = no_augmentation_receipt(
        module_id="hedonic_preference",
        exact_scope="P1/LIKING/HEART",
        input_sha256="1" * 64,
        evidence_sha256="2" * 64,
        policy_sha256="3" * 64,
        reasons=("QUESTION_ALREADY_RESOLVED",),
    )
    packet = CriterionFitPacketV2(
        parent_v1=parent,
        preference_fit_evidence_v2_sha256="4" * 64,
        hedonic_state="VALIDATED_EXACT_SCOPE",
        cluster_bootstrap_sha256="5" * 64,
        heldout_validation_sha256="6" * 64,
        transitivity_sha256="7" * 64,
        next_pair_sha256="8" * 64,
        evidence_delta_receipt=receipt,
        test_only=True,
    )

    assert CriterionFitPacketV2.from_dict(packet.as_dict()) == packet
    assert packet.as_dict()["authority_flags"] == AUTHORITY_FLAGS_FALSE


def _criterion_fit_v2_parent_for_v3() -> CriterionFitPacketV2:
    parent_v1 = replace(
        _records()[7],
        criterion="LIKING",
        validation_state="DIAGNOSTIC",
    )
    receipt = no_augmentation_receipt(
        module_id="hedonic_preference",
        exact_scope="P1/LIKING",
        input_sha256="1" * 64,
        evidence_sha256="2" * 64,
        policy_sha256="3" * 64,
        reasons=("V3_BINDING_REQUIRED",),
    )
    return CriterionFitPacketV2(
        parent_v1=parent_v1,
        preference_fit_evidence_v2_sha256="4" * 64,
        hedonic_state="DIAGNOSTIC",
        cluster_bootstrap_sha256="5" * 64,
        heldout_validation_sha256="6" * 64,
        transitivity_sha256="7" * 64,
        next_pair_sha256="8" * 64,
        evidence_delta_receipt=receipt,
        test_only=True,
    )


def test_criterion_fit_v3_rejects_validated_state_without_bound_evidence() -> None:
    receipt = no_augmentation_receipt(
        module_id="hedonic_preference_v3",
        exact_scope="P1/LIKING",
        input_sha256="9" * 64,
        evidence_sha256="4" * 64,
        policy_sha256="a" * 64,
        reasons=("MISSING_BINDINGS",),
    )
    with pytest.raises(ValueError, match="VALIDATED_EXACT_SCOPE requires"):
        CriterionFitPacketV3(
            parent_v2=_criterion_fit_v2_parent_for_v3(),
            preference_fit_evidence_v3_sha256=None,
            evaluation_context_sha256=None,
            item_bindings_sha256=None,
            order_carryover_sha256=None,
            adequacy_contract_sha256=None,
            hedonic_state="VALIDATED_EXACT_SCOPE",
            evidence_delta_receipt=receipt,
            test_only=True,
        )


def test_criterion_fit_v3_rejects_augmentation_for_nonvalidated_state() -> None:
    v3_sha = "9" * 64
    binding_hashes = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)
    delta = DecisionDeltaV1(
        delta_id="HEDONIC-V3-TEST",
        decision_effect="Use exact-scope liking evidence only.",
        observed_facts=("one exact-scope result",),
        derived_calculations=(),
        hypotheses=(),
        forbidden_inferences=("No universal liking authority.",),
    )
    receipt = EvidenceDeltaReceiptV1(
        module_id="hedonic_preference_v3",
        exact_scope="P1/LIKING",
        state=EvidenceAugmentationState.AUGMENT,
        input_sha256="e" * 64,
        evidence_sha256=v3_sha,
        policy_sha256="f" * 64,
        source_binding_sha256=(v3_sha, *binding_hashes),
        reason_codes=("FULLY_BOUND",),
        delta=delta,
        blockers=(),
        next_action=None,
    )
    with pytest.raises(ValueError, match="only VALIDATED_EXACT_SCOPE may AUGMENT"):
        CriterionFitPacketV3(
            parent_v2=_criterion_fit_v2_parent_for_v3(),
            preference_fit_evidence_v3_sha256=v3_sha,
            evaluation_context_sha256=binding_hashes[0],
            item_bindings_sha256=binding_hashes[1],
            order_carryover_sha256=binding_hashes[2],
            adequacy_contract_sha256=binding_hashes[3],
            hedonic_state="WITHHELD",
            evidence_delta_receipt=receipt,
            test_only=True,
        )


def test_criterion_fit_v3_rejects_partial_bindings_and_parent_mode_mismatch() -> None:
    receipt = no_augmentation_receipt(
        module_id="hedonic_preference_v3",
        exact_scope="P1/LIKING",
        input_sha256="9" * 64,
        evidence_sha256="4" * 64,
        policy_sha256="a" * 64,
        reasons=("WITHHELD",),
    )
    with pytest.raises(ValueError, match="all present or all absent"):
        CriterionFitPacketV3(
            parent_v2=_criterion_fit_v2_parent_for_v3(),
            preference_fit_evidence_v3_sha256="b" * 64,
            evaluation_context_sha256=None,
            item_bindings_sha256=None,
            order_carryover_sha256=None,
            adequacy_contract_sha256=None,
            hedonic_state="WITHHELD",
            evidence_delta_receipt=receipt,
            test_only=True,
        )
    with pytest.raises(ValueError, match="test_only must match parent_v2"):
        CriterionFitPacketV3(
            parent_v2=_criterion_fit_v2_parent_for_v3(),
            preference_fit_evidence_v3_sha256=None,
            evaluation_context_sha256=None,
            item_bindings_sha256=None,
            order_carryover_sha256=None,
            adequacy_contract_sha256=None,
            hedonic_state="WITHHELD",
            evidence_delta_receipt=receipt,
            test_only=False,
        )
