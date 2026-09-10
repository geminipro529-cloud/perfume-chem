from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.hedonic_evidence import EvaluationSubstrate, SensoryEvaluationContext
from engine.sensory.ledger import (
    ObservationCellKey,
    SensorySafetyEvent,
    TemporalObservationCell,
)
from engine.sensory.order_balance import PresentationSchedule, generate_williams_schedule
from engine.solforge.adapters import (
    analyze_execution_receipt,
    audit_execution_receipt_v2,
    build_criterion_fit_packet,
    build_criterion_fit_packet_v2,
    build_criterion_fit_packet_v3,
    build_temporal_packet,
)
from engine.solforge.contracts import CriterionFitPacketV3, ExecutionReceiptV1

H = "a" * 64


def _cell(
    sample: str,
    value: float,
    *,
    observation: str | None = None,
    repeat: str = "R1",
    assessor: str = "A1",
) -> dict:
    return TemporalObservationCell(
        key=ObservationCellKey(
            protocol_id="P1", sample_id=sample, assessor_id=assessor,
            repeat_id=repeat, time_seconds=0, endpoint_id="DEPTH",
        ),
        observation_id=observation or f"O-{sample}-{assessor}-{repeat}",
        value=value,
        presentation_sequence_id="SEQ-1",
        presentation_position=1 if sample == "CONTROL" else 2,
    ).as_dict()


def _comparisons(*, criterion: str = "DEPTH", ties: bool = False) -> list[dict]:
    records = []
    winners = ("TREATMENT", None if ties else "TREATMENT", "CONTROL", "TREATMENT")
    for index, winner in enumerate(winners, start=1):
        records.append(
            {
                "left_item": "CONTROL", "right_item": "TREATMENT",
                "preferred_item": winner, "comparison_id": f"C{index}",
                "assessor_id": "A1" if index % 2 else "A2", "protocol_id": "P1",
                "criterion_id": criterion, "time_seconds": 0,
                "first_presented_item": "CONTROL" if index % 2 else "TREATMENT",
                "repeat_id": "R1", "partition": "training" if index <= 3 else "heldout",
            }
        )
    return records


def _execution(**context_changes) -> ExecutionReceiptV1:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))
    context = {
        "protocol_scope": {
            "protocol_id": "P1", "sample_ids": ["CONTROL", "TREATMENT"],
            "assessor_ids": ["A1"], "repeat_ids": ["R1"],
            "timepoints_seconds": [0.0], "endpoint_ids": ["DEPTH"],
            "schedule_sha256": schedule.schedule_sha256,
            "within_sniff": False, "within_sniff_apparatus_qualified": False,
            "within_sniff_timing_protocol_qualified": False,
            "require_repeatability": False,
            "maximum_within_assessor_repeat_spread": None,
        },
        "schedule": schedule.as_dict(),
        "observations": [_cell("CONTROL", 2.0), _cell("TREATMENT", 4.0)],
        "safety_events": [],
        "comparisons": _comparisons(),
        "preference_fit": {
            "minimum_comparisons": 2, "minimum_heldout_comparisons": 1,
            "declared_baseline_accuracy": 0.4, "bootstrap_replicates": 8,
            "bootstrap_seed": 17, "require_scoped_validation": True,
        },
        "formula_build_sha256": "f" * 64,
        "hedonic_scope": "OWNER",
    }
    context.update(context_changes)
    return ExecutionReceiptV1(
        compiled_experiment_sha256=H, executor="SYNTHETIC_FIXTURE",
        execution_context=context,
        sample_sha256=(("CONTROL", "c" * 64), ("TREATMENT", "d" * 64)),
        deviations=(), test_only=True,
    )


def test_missing_and_duplicate_cells_are_not_interpolated() -> None:
    missing_execution = _execution(observations=[_cell("CONTROL", 2.0)])
    missing = analyze_execution_receipt(missing_execution)
    missing_packet = build_temporal_packet(missing_execution, missing)
    duplicate_execution = _execution(
        observations=[
            _cell("CONTROL", 2.0),
            _cell("CONTROL", 2.1, observation="O-DUP"),
            _cell("TREATMENT", 4.0),
        ]
    )
    duplicate = analyze_execution_receipt(duplicate_execution)
    assert missing_packet.state == "INSUFFICIENT"
    assert missing.interpolated_cell_count == 0
    assert duplicate.state.value == "HOLD"
    assert duplicate.duplicate_cells


def test_order_imbalance_and_unqualified_within_sniff_hold() -> None:
    bad_schedule = PresentationSchedule(
        labels=("CONTROL", "TREATMENT"),
        sequences=(("CONTROL", "TREATMENT"), ("CONTROL", "TREATMENT")),
    )
    base = _execution().as_dict()["execution_context"]
    scope = dict(base["protocol_scope"])
    scope.update(
        schedule_sha256=bad_schedule.schedule_sha256,
        within_sniff=True,
        within_sniff_apparatus_qualified=False,
        within_sniff_timing_protocol_qualified=False,
    )
    result = analyze_execution_receipt(
        _execution(protocol_scope=scope, schedule=bad_schedule.as_dict())
    )
    assert result.state.value == "HOLD"
    assert any("within-sniff" in blocker for blocker in result.blockers)
    assert any("balanced" in blocker for blocker in result.blockers)


def test_safety_event_and_repeatability_failure_hold() -> None:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))
    scope = _execution().as_dict()["execution_context"]["protocol_scope"]
    scope = {
        **scope, "repeat_ids": ["R1", "R2"], "require_repeatability": True,
        "maximum_within_assessor_repeat_spread": 0.5,
    }
    safety = SensorySafetyEvent(
        event_id="S1", protocol_id="P1", assessor_id="A1", sample_id="CONTROL",
        time_seconds=0, event_code="HEADACHE", note="stop",
    ).as_dict()
    observations = [
        _cell("CONTROL", 1.0, repeat="R1"), _cell("CONTROL", 4.0, repeat="R2"),
        _cell("TREATMENT", 3.0, repeat="R1"), _cell("TREATMENT", 3.1, repeat="R2"),
    ]
    result = analyze_execution_receipt(
        _execution(
            protocol_scope=scope, schedule=schedule.as_dict(),
            observations=observations, safety_events=[safety],
        )
    )
    assert result.state.value == "HOLD"
    assert result.safety_stop_triggered is True
    assert result.assessor_reliability_state.value == "HOLD"


def test_temporal_packet_is_deterministic_and_test_only_has_no_authority() -> None:
    execution = _execution()
    result = analyze_execution_receipt(execution)
    first = build_temporal_packet(execution, result)
    second = build_temporal_packet(execution, result)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.as_dict()["authority_flags"] == {
        "compounding": False, "hedonic": False, "physical_execution": False,
        "purchase": False, "release": False, "safety": False, "sensory": False,
    }


def test_criterion_mixing_and_disconnected_graph_are_withheld() -> None:
    mixed = _comparisons()
    mixed[1] = {**mixed[1], "criterion_id": "RICHNESS"}
    execution = _execution(comparisons=mixed)
    temporal = build_temporal_packet(execution, analyze_execution_receipt(execution))
    packet = build_criterion_fit_packet(execution, temporal, criterion="DEPTH")
    assert packet.validation_state == "WITHHELD"

    disconnected = _comparisons() + [
            {
                **_comparisons()[0], "left_item": "THIRD", "right_item": "FOURTH",
                "preferred_item": "THIRD", "comparison_id": "C9",
                "first_presented_item": "THIRD",
            }
    ]
    execution2 = _execution(comparisons=disconnected)
    temporal2 = build_temporal_packet(execution2, analyze_execution_receipt(execution2))
    packet2 = build_criterion_fit_packet(execution2, temporal2, criterion="DEPTH")
    assert packet2.validation_state == "WITHHELD"


def test_ties_heterogeneity_order_effect_and_next_pair_are_retained() -> None:
    execution = _execution(comparisons=_comparisons(ties=True))
    temporal = build_temporal_packet(execution, analyze_execution_receipt(execution))
    packet = build_criterion_fit_packet(execution, temporal, criterion="DEPTH")
    assert packet.tie_rate > 0
    assert packet.assessor_heterogeneity is not None
    assert packet.order_effect is not None
    assert packet.next_pair == ("CONTROL", "TREATMENT")
    assert packet.record_sha256 == build_criterion_fit_packet(
        execution, temporal, criterion="DEPTH"
    ).record_sha256


def test_heldout_baseline_failure_and_liking_gate_remain_scoped() -> None:
    config = _execution().as_dict()["execution_context"]["preference_fit"]
    config = {**config, "declared_baseline_accuracy": 1.0}
    execution = _execution(preference_fit=config)
    temporal = build_temporal_packet(execution, analyze_execution_receipt(execution))
    depth = build_criterion_fit_packet(execution, temporal, criterion="DEPTH")
    assert depth.validation_state == "FAILED_BASELINE"

    liking_comparisons = _comparisons(criterion="LIKING")
    liking_execution = _execution(comparisons=liking_comparisons)
    liking_temporal = build_temporal_packet(
        liking_execution, analyze_execution_receipt(liking_execution)
    )
    liking = build_criterion_fit_packet(
        liking_execution, liking_temporal, criterion="LIKING"
    )
    assert liking.validation_state == "FAILED_BASELINE"
    assert liking.test_only is True


def test_temporal_parent_change_changes_descendant_hash() -> None:
    execution = _execution()
    first = build_temporal_packet(execution, analyze_execution_receipt(execution))
    changed = replace(execution, deviations=("one-byte-parent-change",))
    second = build_temporal_packet(changed, analyze_execution_receipt(changed))
    assert first.record_sha256 != second.record_sha256


def test_v2_execution_adapter_maps_insufficient_and_conflicted_dispositions() -> None:
    resolved = audit_execution_receipt_v2(_execution())
    conflicted_execution = _execution(
        observations=[
            _cell("CONTROL", 2.0),
            _cell("CONTROL", 2.1, observation="O-DUP"),
            _cell("TREATMENT", 4.0),
        ]
    )
    conflicted = audit_execution_receipt_v2(conflicted_execution)

    assert resolved.disposition.value == "INSUFFICIENT_SCOPE"
    assert conflicted.disposition.value == "CONFLICTED"
    assert conflicted.receipt.evidence_sha256 != resolved.receipt.evidence_sha256
    assert conflicted.receipt.next_action == (
        "AUDIT_PROVENANCE:protocol/sample/assessor/repeat/timepoint/endpoint"
    )


def test_v2_liking_adapter_binds_proper_validation_and_delta_receipts() -> None:
    protocol_sha256 = sha256_hex(
        canonical_json_bytes(
            _execution().as_dict()["execution_context"]["protocol_scope"]
        )
    )
    comparisons: list[dict] = []
    outcomes = (
        ("A1", "TREATMENT", "CONTROL"),
        ("A1", "TREATMENT", "TREATMENT"),
        ("A1", None, "CONTROL"),
        ("A2", "TREATMENT", "TREATMENT"),
        ("A2", "TREATMENT", "CONTROL"),
        ("A2", None, "TREATMENT"),
    )
    for index, (assessor, preferred, first) in enumerate(outcomes, start=1):
        comparisons.append(
            {
                "left_item": "CONTROL",
                "right_item": "TREATMENT",
                "preferred_item": preferred,
                "comparison_id": f"T{index}",
                "assessor_id": assessor,
                "protocol_id": "P1",
                "criterion_id": "LIKING",
                "time_seconds": 0,
                "first_presented_item": first,
                "repeat_id": "R1",
                "partition": "training",
                "session_id": f"{assessor}-S{index}",
                "matrix_id": "M1",
                "time_window_id": "OPENING",
                "position_in_session": 1,
                "protocol_sha256": protocol_sha256,
                "sample_sha256": "c" * 64,
            }
        )
    for index in range(1, 4):
        comparisons.append(
            {
                **comparisons[0],
                "comparison_id": f"H{index}",
                "assessor_id": "A3",
                "preferred_item": "TREATMENT",
                "first_presented_item": "CONTROL" if index % 2 else "TREATMENT",
                "partition": "heldout",
                "session_id": f"A3-H{index}",
            }
        )
    config = {
        "minimum_comparisons": 4,
        "minimum_heldout_comparisons": 3,
        "declared_baseline_accuracy": 0.4,
        "bootstrap_replicates": 8,
        "bootstrap_seed": 17,
        "require_scoped_validation": True,
    }
    v2_config = {
        "construct_registry_sha256": "3" * 64,
        "criterion_wording_sha256": "4" * 64,
        "source_transfer_sha256": "5" * 64,
        "source_transfer_state": "NARROWER_SCOPE",
        "bootstrap_replicates": 20,
        "bootstrap_seed": 17,
        "heldout_bootstrap_replicates": 20,
        "heldout_seed": 17,
        "practical_margin": 0.0,
        "split_unit": "ASSESSOR",
        "decision_resolved": True,
    }
    execution = _execution(
        comparisons=comparisons,
        preference_fit=config,
        preference_fit_v2=v2_config,
    )
    temporal = build_temporal_packet(execution, analyze_execution_receipt(execution))
    packet = build_criterion_fit_packet_v2(execution, temporal, criterion="LIKING")

    assert packet.preference_fit_evidence_v2_sha256 is not None
    assert packet.heldout_validation_sha256 is not None
    assert packet.cluster_bootstrap_sha256 is not None
    assert packet.hedonic_state == "DIAGNOSTIC"
    assert packet.evidence_delta_receipt.state.value == "HOLD"
    assert "V3_ITEM_CONTEXT_BINDING_REQUIRED" in packet.evidence_delta_receipt.blockers
    assert set(packet.evidence_delta_receipt.authority.values()) == {False}

    malformed_config = {
        **config,
        "require_scoped_validation": "false",
    }
    malformed_execution = _execution(
        comparisons=comparisons,
        preference_fit=malformed_config,
        preference_fit_v2=v2_config,
    )
    malformed_temporal = build_temporal_packet(
        malformed_execution,
        analyze_execution_receipt(malformed_execution),
    )
    with pytest.raises(
        TypeError,
        match="require_scoped_validation must be boolean",
    ):
        build_criterion_fit_packet_v2(
            malformed_execution,
            malformed_temporal,
            criterion="LIKING",
        )


def test_v3_liking_adapter_binds_item_sample_context_order_and_adequacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_execution = _execution()
    protocol_sha256 = sha256_hex(
        canonical_json_bytes(
            base_execution.as_dict()["execution_context"]["protocol_scope"]
        )
    )
    evaluation_context = SensoryEvaluationContext(
        context_id="blotter-v3",
        substrate=EvaluationSubstrate.BLOTTER,
        application_protocol_sha256="6" * 64,
        environment_sha256="7" * 64,
        maturation_state_sha256="8" * 64,
        carryover_control_sha256="9" * 64,
        carryover_qualified=True,
        apparatus_sha256="a" * 64,
    )
    comparisons: list[dict] = []
    outcomes = (
        ("A1", "TREATMENT", "CONTROL"),
        ("A1", "TREATMENT", "TREATMENT"),
        ("A1", None, "CONTROL"),
        ("A2", "TREATMENT", "TREATMENT"),
        ("A2", "TREATMENT", "CONTROL"),
        ("A2", None, "TREATMENT"),
    )
    for index, (assessor, preferred, first) in enumerate(outcomes, start=1):
        comparisons.append(
            {
                "left_item": "CONTROL",
                "right_item": "TREATMENT",
                "preferred_item": preferred,
                "comparison_id": f"T{index}",
                "assessor_id": assessor,
                "protocol_id": "P1",
                "criterion_id": "LIKING",
                "time_seconds": 0,
                "first_presented_item": first,
                "repeat_id": "R1",
                "partition": "training",
                "session_id": f"{assessor}-S{index}",
                "matrix_id": "M1",
                "time_window_id": "OPENING",
                "position_in_session": 1,
                "protocol_sha256": protocol_sha256,
                "sample_sha256": "c" * 64,
                "left_sample_sha256": "c" * 64,
                "right_sample_sha256": "d" * 64,
                "evaluation_context_sha256": evaluation_context.record_sha256,
            }
        )
    for index in range(1, 4):
        comparisons.append(
            {
                **comparisons[0],
                "comparison_id": f"H{index}",
                "assessor_id": "A3",
                "preferred_item": "TREATMENT",
                "first_presented_item": (
                    "CONTROL" if index % 2 else "TREATMENT"
                ),
                "partition": "heldout",
                "session_id": f"A3-H{index}",
            }
        )
    preference_fit = {
        "minimum_comparisons": 4,
        "minimum_heldout_comparisons": 3,
        "declared_baseline_accuracy": 0.4,
        "bootstrap_replicates": 8,
        "bootstrap_seed": 17,
        "require_scoped_validation": True,
    }
    preference_fit_v2 = {
        "construct_registry_sha256": "3" * 64,
        "criterion_wording_sha256": "4" * 64,
        "source_transfer_sha256": "5" * 64,
        "source_transfer_state": "NARROWER_SCOPE",
        "bootstrap_replicates": 20,
        "bootstrap_seed": 17,
        "heldout_bootstrap_replicates": 20,
        "heldout_seed": 17,
        "practical_margin": 0.0,
        "split_unit": "ASSESSOR",
        "decision_resolved": True,
    }
    preference_fit_v3 = {
        "focal_item_id": "TREATMENT",
        "item_bindings": [
            {
                "item_id": "CONTROL",
                "build_sha256": "0" * 64,
                "sample_sha256": "c" * 64,
                "provenance_manifest_sha256": "1" * 64,
                "sampling_or_dose_receipt_sha256": "2" * 64,
                "batch_id": "control-batch",
            },
            {
                "item_id": "TREATMENT",
                "build_sha256": "f" * 64,
                "sample_sha256": "d" * 64,
                "provenance_manifest_sha256": "3" * 64,
                "sampling_or_dose_receipt_sha256": "4" * 64,
                "batch_id": "treatment-batch",
            },
        ],
        "evaluation_context": {
            key: value
            for key, value in evaluation_context.as_dict().items()
            if key not in {"schema_version", "authority"}
        },
        "adequacy_contract": {
            "analysis_plan_sha256": "a" * 64,
            "sampling_frame_sha256": "b" * 64,
            "minimum_assessors": 3,
            "minimum_directional_training_comparisons": 4,
            "minimum_heldout_groups": 1,
            "minimum_heldout_comparisons": 3,
            "minimum_cluster_bootstrap_replicates": 20,
            "minimum_heldout_bootstrap_replicates": 20,
        },
        "order_carryover": {
            "maximum_pair_order_count_difference": 1,
            "maximum_absolute_first_position_effect": 0.25,
            "require_qualified_carryover": True,
        },
    }
    execution = _execution(
        comparisons=comparisons,
        preference_fit=preference_fit,
        preference_fit_v2=preference_fit_v2,
        preference_fit_v3=preference_fit_v3,
    )
    temporal = build_temporal_packet(execution, analyze_execution_receipt(execution))
    packet = build_criterion_fit_packet_v3(
        execution,
        temporal,
        criterion="LIKING",
    )

    assert packet.hedonic_state == "VALIDATED_EXACT_SCOPE"
    assert packet.preference_fit_evidence_v3_sha256 is not None
    assert packet.evaluation_context_sha256 == evaluation_context.record_sha256
    assert packet.item_bindings_sha256 is not None
    assert packet.order_carryover_sha256 is not None
    assert packet.adequacy_contract_sha256 is not None
    assert packet.evidence_delta_receipt.state.value == "AUGMENT"
    assert CriterionFitPacketV3.from_dict(packet.as_dict()) == packet

    malformed_context = execution.as_dict()["execution_context"]
    malformed_context["preference_fit_v3"]["evaluation_context"][
        "carryover_qualified"
    ] = "false"
    malformed_execution = replace(
        execution,
        execution_context=malformed_context,
    )
    malformed_temporal = build_temporal_packet(
        malformed_execution,
        analyze_execution_receipt(malformed_execution),
    )
    malformed = build_criterion_fit_packet_v3(
        malformed_execution,
        malformed_temporal,
        criterion="LIKING",
    )
    assert malformed.hedonic_state == "WITHHELD"
    assert malformed.evidence_delta_receipt.state.value == "HOLD"
    assert "carryover_qualified must be boolean" in " ".join(
        malformed.evidence_delta_receipt.blockers
    )

    mismatched_parent = replace(
        packet.parent_v2,
        preference_fit_evidence_v2_sha256="e" * 64,
    )
    monkeypatch.setattr(
        "engine.solforge.adapters.build_criterion_fit_packet_v2",
        lambda *_args, **_kwargs: mismatched_parent,
    )
    mismatched = build_criterion_fit_packet_v3(
        execution,
        temporal,
        criterion="LIKING",
    )
    assert mismatched.hedonic_state == "WITHHELD"
    assert "does not match reconstructed V2 evidence" in " ".join(
        mismatched.evidence_delta_receipt.blockers
    )
