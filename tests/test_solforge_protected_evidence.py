from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from engine.evidence.augmentation import hold_receipt
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.sensory.ledger import ObservationCellKey, TemporalObservationCell
from engine.sensory.order_balance import generate_williams_schedule
from engine.solforge.benchmark import (
    BENCHMARK_AUTHORITY_FLAGS,
    BenchmarkCaseV1,
    BenchmarkPhase,
    ConditionKind,
    compile_conditions,
    freeze_sol_output,
)
from engine.solforge.contracts import ExecutionReceiptV1
from engine.solforge.protected_evidence import (
    ProtectedConditionSetV1,
    ProtectedEvidenceBenchmarkCaseV1,
    ProtectedEvidenceCapsuleV1,
    ProtectedEvidenceModule,
    build_protected_evidence_capsule,
    build_protected_evidence_capsule_from_execution,
    compile_protected_evidence_conditions,
    score_protected_evidence_invariants,
)


def _case() -> BenchmarkCaseV1:
    return BenchmarkCaseV1(
        case_id="PE-TEM-S01",
        phase=BenchmarkPhase.SCREEN,
        category="protected temporal evidence",
        system_prompt="Resolve the supplied evidence without inventing observations.",
        user_prompt="Choose the evidence-safe next action.",
        input_payload={
            "criterion": "DEPTH",
            "evidence_module": "TEMPORAL_SENSORY_LEDGER",
        },
        public_invariants=("authority_false", "next_comparison"),
        sealed_answer_key={"allowed_decisions": ["HOLD"], "max_interventions": 0},
    )


def _hedonic_case() -> BenchmarkCaseV1:
    return BenchmarkCaseV1(
        case_id="PE-HED-S01",
        phase=BenchmarkPhase.SCREEN,
        category="protected hedonic evidence",
        system_prompt="Use only criterion-scoped blinded comparison evidence.",
        user_prompt="Choose the evidence-safe next action.",
        input_payload={
            "criterion": "LIKING",
            "evidence_module": "HEDONIC_PREFERENCE_LEARNER",
        },
        public_invariants=("authority_false", "criterion_isolation"),
        sealed_answer_key={
            "allowed_decisions": ["PROPOSED"],
            "max_interventions": 1,
            "required_criterion": "LIKING",
        },
    )


def _frozen(case: BenchmarkCaseV1):
    output_text = json.dumps(
        {
            "decision": "PROPOSED",
            "interventions": [{"kind": "MODEL_AUTHORED"}],
            "target_linked_reasoning": "The model wants to proceed.",
            "objective_receipt": {
                "decision_state": "PROPOSED",
                "authority": {"sensory": True},
            },
            "authority_flags": {"sensory": True},
        },
        sort_keys=True,
    )
    return freeze_sol_output(
        case,
        {
            "case_id": case.case_id,
            "phase": case.phase.value,
            "model_identity": "GPT-5.6 Sol",
            "reasoning_setting": "xhigh",
            "conversation_id": "fresh-projectless-pe-tem-s01",
            "output_text": output_text,
        },
    )


def _temporal_execution() -> ExecutionReceiptV1:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))

    def cell(
        sample: str,
        time_seconds: float,
        value: float,
        assessor: str,
        sequence_index: int,
    ) -> dict[str, object]:
        sequence = schedule.sequences[sequence_index]
        return TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id="P1",
                sample_id=sample,
                assessor_id=assessor,
                repeat_id="R1",
                time_seconds=time_seconds,
                endpoint_id="DEPTH",
            ),
            observation_id=f"O-{sample}-{assessor}-{time_seconds:g}",
            value=value,
            presentation_sequence_id=f"sequence-{sequence_index + 1}",
            presentation_position=sequence.index(sample) + 1,
        ).as_dict()

    return ExecutionReceiptV1(
        compiled_experiment_sha256="a" * 64,
        executor="SYNTHETIC_BENCHMARK_FIXTURE",
        execution_context={
            "protocol_scope": {
                "protocol_id": "P1",
                "sample_ids": ["CONTROL", "TREATMENT"],
                "assessor_ids": ["A1", "A2"],
                "repeat_ids": ["R1"],
                "timepoints_seconds": [0.0, 300.0],
                "endpoint_ids": ["DEPTH"],
                "schedule_sha256": schedule.schedule_sha256,
                "within_sniff": False,
                "within_sniff_apparatus_qualified": False,
                "within_sniff_timing_protocol_qualified": False,
                "require_repeatability": False,
                "maximum_within_assessor_repeat_spread": None,
            },
            "schedule": schedule.as_dict(),
            "observations": [
                cell(sample, timepoint, value, assessor, assessor_index)
                for assessor_index, assessor in enumerate(("A1", "A2"))
                for sample, values in (
                    ("CONTROL", (3.0, 3.0)),
                    ("TREATMENT", (2.0, 4.5)),
                )
                for timepoint, value in zip((0.0, 300.0), values, strict=True)
            ],
            "safety_events": [],
        },
        sample_sha256=(("CONTROL", "b" * 64), ("TREATMENT", "c" * 64)),
        deviations=(),
        test_only=True,
    )


def _hedonic_execution() -> ExecutionReceiptV1:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))
    protocol_scope = {
        "protocol_id": "P1",
        "sample_ids": ["CONTROL", "TREATMENT"],
        "assessor_ids": ["A1", "A2"],
        "repeat_ids": ["R1"],
        "timepoints_seconds": [0.0],
        "endpoint_ids": ["DEPTH"],
        "schedule_sha256": schedule.schedule_sha256,
        "within_sniff": False,
        "within_sniff_apparatus_qualified": False,
        "within_sniff_timing_protocol_qualified": False,
        "require_repeatability": False,
        "maximum_within_assessor_repeat_spread": None,
    }
    protocol_sha256 = sha256_hex(canonical_json_bytes(protocol_scope))
    comparisons: list[dict[str, object]] = []
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
                "sample_sha256": "b" * 64,
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

    def cell(
        sample: str,
        value: float,
        assessor: str,
        sequence_index: int,
    ) -> dict[str, object]:
        sequence = schedule.sequences[sequence_index]
        return TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id="P1",
                sample_id=sample,
                assessor_id=assessor,
                repeat_id="R1",
                time_seconds=0.0,
                endpoint_id="DEPTH",
            ),
            observation_id=f"O-{sample}-{assessor}",
            value=value,
            presentation_sequence_id=f"sequence-{sequence_index + 1}",
            presentation_position=sequence.index(sample) + 1,
        ).as_dict()

    return ExecutionReceiptV1(
        compiled_experiment_sha256="a" * 64,
        executor="SYNTHETIC_BENCHMARK_FIXTURE",
        execution_context={
            "protocol_scope": protocol_scope,
            "schedule": schedule.as_dict(),
            "observations": [
                cell(sample, value, assessor, assessor_index)
                for assessor_index, assessor in enumerate(("A1", "A2"))
                for sample, value in (("CONTROL", 2.0), ("TREATMENT", 4.0))
            ],
            "safety_events": [],
            "comparisons": comparisons,
            "preference_fit": {
                "minimum_comparisons": 4,
                "minimum_heldout_comparisons": 3,
                "declared_baseline_accuracy": 0.4,
                "bootstrap_replicates": 8,
                "bootstrap_seed": 17,
                "require_scoped_validation": True,
            },
            "preference_fit_v2": {
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
                "decision_resolved": False,
            },
            "formula_build_sha256": "f" * 64,
            "hedonic_scope": "TRAINED_PANEL",
        },
        sample_sha256=(("CONTROL", "b" * 64), ("TREATMENT", "c" * 64)),
        deviations=(),
        test_only=True,
    )


def test_protected_temporal_receipt_overrides_model_authored_objective_fields() -> None:
    case = _case()
    frozen = _frozen(case)
    receipt = hold_receipt(
        module_id="temporal_sensory_ledger",
        exact_scope="P1/TEMPORAL",
        input_sha256="1" * 64,
        evidence_sha256="2" * 64,
        policy_sha256="3" * 64,
        source_binding_sha256=("4" * 64,),
        reasons=("CANONICAL_CELL_CONFLICT",),
        blockers=("duplicate canonical observation cells require provenance audit",),
        next_action=(
            "AUDIT_PROVENANCE:protocol/sample/assessor/repeat/timepoint/endpoint"
        ),
    )
    capsule = build_protected_evidence_capsule(
        case_id=case.case_id,
        module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
        execution_receipt_sha256="5" * 64,
        objective_receipt=receipt,
    )

    protected = compile_protected_evidence_conditions(case, frozen, capsule)
    ordinary = compile_conditions(case, frozen)
    by_kind = {condition.condition: condition for condition in protected.conditions}
    payload = json.loads(by_kind[ConditionKind.SOLFORGE].output_text.rstrip())

    assert payload["decision"] == "HOLD"
    assert payload["interventions"] == []
    assert payload["objective_receipt"] == receipt.as_dict()
    assert payload["objective_receipt_sha256"] == receipt.receipt_sha256
    assert payload["execution_receipt_sha256"] == "5" * 64
    assert payload["authority_flags"] == BENCHMARK_AUTHORITY_FLAGS
    assert payload["secondary_explanation"] == "The model wants to proceed."
    assert protected.capsule == capsule
    assert protected.frozen_sol_output_sha256 == frozen.record_sha256
    assert len(by_kind[ConditionKind.NO_OP_LENGTH_MATCHED].output_text.encode("utf-8")) == len(
        by_kind[ConditionKind.SOLFORGE].output_text.encode("utf-8")
    )
    assert (
        ordinary[0].frozen_sol_output_sha256
        == by_kind[ConditionKind.SOLFORGE].frozen_sol_output_sha256
    )
    assert canonical_json_bytes(capsule.as_dict()) == capsule.canonical_bytes()


def test_protected_capsule_round_trip_rejects_authority_or_hash_tampering() -> None:
    receipt = hold_receipt(
        module_id="temporal_sensory_ledger",
        exact_scope="P1/TEMPORAL",
        input_sha256="1" * 64,
        evidence_sha256="2" * 64,
        policy_sha256="3" * 64,
        source_binding_sha256=("4" * 64,),
        reasons=("PROTOCOL_INVALID",),
        blockers=("schedule mismatch",),
        next_action="CORRECT_PROTOCOL",
    )
    capsule = build_protected_evidence_capsule(
        case_id="PE-TEM-S02",
        module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
        execution_receipt_sha256="5" * 64,
        objective_receipt=receipt,
    )

    assert ProtectedEvidenceCapsuleV1.from_dict(capsule.as_dict()) == capsule

    authority_tamper = capsule.as_dict()
    authority_tamper["authority_flags"] = {
        **BENCHMARK_AUTHORITY_FLAGS,
        "sensory": True,
    }
    with pytest.raises(ValueError, match="authority_flags"):
        ProtectedEvidenceCapsuleV1.from_dict(authority_tamper)

    hash_tamper = capsule.as_dict()
    hash_tamper["objective_receipt_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="objective receipt hash"):
        ProtectedEvidenceCapsuleV1.from_dict(hash_tamper)


def test_protected_condition_set_rejects_post_compilation_receipt_tampering() -> None:
    case = _case()
    frozen = _frozen(case)
    receipt = hold_receipt(
        module_id="temporal_sensory_ledger",
        exact_scope="P1/TEMPORAL",
        input_sha256="1" * 64,
        evidence_sha256="2" * 64,
        policy_sha256="3" * 64,
        source_binding_sha256=("4" * 64,),
        reasons=("PROTOCOL_INVALID",),
        blockers=("schedule mismatch",),
        next_action="CORRECT_PROTOCOL",
    )
    capsule = build_protected_evidence_capsule(
        case_id=case.case_id,
        module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
        execution_receipt_sha256="5" * 64,
        objective_receipt=receipt,
    )
    protected = compile_protected_evidence_conditions(case, frozen, capsule)
    treatment = next(
        item for item in protected.conditions if item.condition is ConditionKind.SOLFORGE
    )
    payload = json.loads(treatment.output_text.rstrip())
    payload["objective_receipt"]["reason_codes"] = ["PROTOCOL_TAMPERX"]
    tampered_text = canonical_json_bytes(payload).decode("utf-8")
    tampered_text += " " * (
        len(treatment.output_text.encode("utf-8")) - len(tampered_text.encode("utf-8"))
    )
    tampered_treatment = replace(
        treatment,
        output_text=tampered_text,
        output_sha256=sha256_hex(tampered_text.encode("utf-8")),
    )
    tampered_conditions = tuple(
        tampered_treatment if item.condition is ConditionKind.SOLFORGE else item
        for item in protected.conditions
    )

    with pytest.raises(ValueError, match="does not match capsule"):
        ProtectedConditionSetV1(
            capsule=capsule,
            frozen_sol_output_sha256=frozen.record_sha256,
            conditions=tampered_conditions,
        )


def test_temporal_capsule_is_derived_from_execution_not_model_output() -> None:
    case = _case()
    execution = _temporal_execution()

    capsule = build_protected_evidence_capsule_from_execution(case, execution)

    assert capsule.module is ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER
    assert capsule.execution_receipt_sha256 == execution.record_sha256
    assert capsule.objective_receipt.module_id == "temporal_sensory_ledger"
    assert capsule.objective_receipt.state.value == "AUGMENT"
    assert capsule.objective_receipt.delta is not None
    assert set(capsule.objective_receipt.authority.values()) == {False}


def test_hedonic_capsule_is_derived_from_scoped_validated_comparisons() -> None:
    case = _hedonic_case()
    execution = _hedonic_execution()

    capsule = build_protected_evidence_capsule_from_execution(case, execution)

    assert capsule.module is ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER
    assert capsule.execution_receipt_sha256 == execution.record_sha256
    assert capsule.objective_receipt.module_id == "hedonic_preference"
    assert capsule.objective_receipt.state.value == "AUGMENT"
    assert capsule.objective_receipt.delta is not None
    assert set(capsule.objective_receipt.authority.values()) == {False}


def test_protected_benchmark_case_binds_public_execution_bytes() -> None:
    execution = _temporal_execution()
    base = _case()
    case = replace(
        base,
        input_payload={
            **base.input_payload,
            "execution_receipt": execution.as_dict(),
            "execution_receipt_sha256": execution.record_sha256,
        },
    )

    protected = ProtectedEvidenceBenchmarkCaseV1.from_case(case)

    assert protected.execution == execution
    assert protected.module is ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER
    assert protected.case.input_payload["execution_receipt"] == execution.as_dict()
    assert ProtectedEvidenceBenchmarkCaseV1.from_dict(protected.as_dict()) == protected

    tampered_case = replace(
        case,
        input_payload={
            **case.input_payload,
            "execution_receipt_sha256": "f" * 64,
        },
    )
    with pytest.raises(ValueError, match="execution receipt hash"):
        ProtectedEvidenceBenchmarkCaseV1.from_dict(tampered_case.as_dict())

    derived_tamper = copy.deepcopy(protected.as_dict())
    derived_tamper["prompt_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="derived benchmark fields"):
        ProtectedEvidenceBenchmarkCaseV1.from_dict(derived_tamper)

    exported = protected.as_dict()
    exported["input_payload"]["criterion"] = "RICHNESS"
    assert protected.case.input_payload["criterion"] == "DEPTH"


def test_protected_condition_set_round_trip_and_objective_scoring() -> None:
    execution = _temporal_execution()
    base = _case()
    case = replace(
        base,
        input_payload={
            **base.input_payload,
            "execution_receipt": execution.as_dict(),
            "execution_receipt_sha256": execution.record_sha256,
        },
        sealed_answer_key={
            "allowed_decisions": ["PROPOSED"],
            "max_interventions": 1,
            "required_criterion": "DEPTH",
        },
    )
    benchmark_case = ProtectedEvidenceBenchmarkCaseV1.from_case(case)
    frozen = _frozen(case)
    capsule = build_protected_evidence_capsule_from_execution(case, execution)
    condition_set = compile_protected_evidence_conditions(case, frozen, capsule)

    treatment = next(
        item
        for item in condition_set.conditions
        if item.condition is ConditionKind.SOLFORGE
    )
    payload = json.loads(treatment.output_text.rstrip())

    assert ProtectedConditionSetV1.from_dict(condition_set.as_dict()) == condition_set
    assert payload["evidence_summary"]["observed_cell_count"] == 8
    assert payload["evidence_summary"]["missing_cell_count"] == 0
    assert payload["evidence_summary"]["duplicate_cell_count"] == 0
    assert payload["evidence_summary"]["order_balance_state"] == "PASS_FOR_DESIGN"
    assert payload["evidence_summary"]["summaries"]
    assert payload["evidence_summary"]["transitions"]
    assert payload["next_comparison"].startswith("CONFIRM_FINDING:")

    scores = score_protected_evidence_invariants(benchmark_case, condition_set)
    by_kind = {score.condition: score for score in scores}
    assert by_kind[ConditionKind.SOLFORGE].score == 100
    assert by_kind[ConditionKind.SOLFORGE].critical_errors == ()
    assert by_kind[ConditionKind.PLAIN_SOL].score < 100
    assert "AUTHORITY_ESCALATION" in by_kind[ConditionKind.PLAIN_SOL].critical_errors


def test_unsafe_model_explanation_is_withheld_from_protected_output() -> None:
    execution = _temporal_execution()
    base = _case()
    case = replace(
        base,
        input_payload={
            **base.input_payload,
            "execution_receipt": execution.as_dict(),
            "execution_receipt_sha256": execution.record_sha256,
        },
        sealed_answer_key={
            "allowed_decisions": ["PROPOSED"],
            "max_interventions": 1,
            "required_criterion": "DEPTH",
        },
    )
    output_text = json.dumps(
        {
            "decision": "PROPOSED",
            "interventions": [{"kind": "MODEL_GUESS"}],
            "criterion": "DEPTH",
            "next_comparison": "Proceed.",
            "explanation": "The panel preferred TREATMENT; it is safe and release-ready.",
            "authority_flags": BENCHMARK_AUTHORITY_FLAGS,
        },
        sort_keys=True,
    )
    frozen = freeze_sol_output(
        case,
        {
            "case_id": case.case_id,
            "phase": case.phase.value,
            "model_identity": "GPT-5.6 Sol",
            "reasoning_setting": "xhigh",
            "conversation_id": "fresh-unsafe-explanation",
            "output_text": output_text,
        },
    )
    capsule = build_protected_evidence_capsule_from_execution(case, execution)

    condition_set = compile_protected_evidence_conditions(case, frozen, capsule)
    treatment = next(
        item
        for item in condition_set.conditions
        if item.condition is ConditionKind.SOLFORGE
    )
    payload = json.loads(treatment.output_text.rstrip())
    scores = score_protected_evidence_invariants(
        ProtectedEvidenceBenchmarkCaseV1.from_case(case),
        condition_set,
    )
    treatment_score = next(
        item for item in scores if item.condition is ConditionKind.SOLFORGE
    )

    assert payload["secondary_explanation_state"] == "WITHHELD_UNTRUSTED_CLAIM"
    assert "panel preferred" not in payload["secondary_explanation"].casefold()
    assert "safe" not in payload["secondary_explanation"].casefold()
    assert treatment_score.critical_errors == ()
