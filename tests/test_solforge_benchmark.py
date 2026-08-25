from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.solforge.benchmark import (
    BENCHMARK_AUTHORITY_FLAGS,
    BenchmarkAdmissionV1,
    BenchmarkCaseV1,
    BenchmarkPhase,
    ConditionKind,
    FrozenSolOutputV1,
    JudgeResultV1,
    assert_complete_frozen_outputs,
    blind_condition_outputs,
    compile_conditions,
    freeze_judge_output,
    freeze_sol_output,
    ingest_judge_results,
    score_invariants,
    score_judged_results,
    validate_frozen_sol_output,
)


def _case(*, phase: BenchmarkPhase = BenchmarkPhase.SCREEN) -> BenchmarkCaseV1:
    return BenchmarkCaseV1(
        case_id="CITRUS-001",
        phase=phase,
        category="citrus-free target/no-change",
        system_prompt="Return one bounded hypothesis packet as JSON.",
        user_prompt="The target is a citrus-free orris perfume. Choose the smallest delta.",
        input_payload={
            "target_identity": "citrus-free sweet orris",
            "ideal_architecture": {"citrus": "absent", "orris": "central"},
            "current_inventory_build": {"materials": ["Orris Givco"]},
            "criterion": "TARGET_FIDELITY",
        },
        public_invariants=(
            "correct_no_change",
            "target_inventory_separation",
            "authority_false",
        ),
        sealed_answer_key={
            "allowed_decisions": ["NO_CHANGE"],
            "max_interventions": 0,
            "required_blockers": [],
            "forbidden_materials": ["Neroli", "Bergamot"],
            "require_authority_false": True,
            "require_ideal_inventory_separation": True,
            "require_next_comparison": True,
        },
    )


def _frozen(case: BenchmarkCaseV1) -> FrozenSolOutputV1:
    output = json.dumps(
        {
            "decision": "NO_CHANGE",
            "interventions": [],
            "blockers": [],
            "materials": [],
            "next_comparison": "Retain the citrus-free control.",
            "authority_flags": BENCHMARK_AUTHORITY_FLAGS,
        },
        sort_keys=True,
    )
    return FrozenSolOutputV1(
        case_id=case.case_id,
        phase=case.phase,
        model_identity="GPT-5.6 Sol",
        reasoning_setting="xhigh",
        conversation_id="projectless-task-001",
        prompt_sha256=case.prompt_sha256,
        input_sha256=case.input_sha256,
        output_text=output,
        output_sha256=sha256_hex(output.encode("utf-8")),
    )


def test_frozen_output_rejects_unknown_model_reasoning_and_hash_drift() -> None:
    case = _case()
    frozen = _frozen(case)
    validate_frozen_sol_output(case, frozen)
    with pytest.raises(ValueError, match="model identity"):
        validate_frozen_sol_output(case, replace(frozen, model_identity="GPT-5"))
    with pytest.raises(ValueError, match="reasoning setting"):
        validate_frozen_sol_output(case, replace(frozen, reasoning_setting="high"))
    with pytest.raises(ValueError, match="prompt hash"):
        validate_frozen_sol_output(case, replace(frozen, prompt_sha256="a" * 64))
    with pytest.raises(ValueError, match="output hash"):
        validate_frozen_sol_output(case, replace(frozen, output_sha256="b" * 64))


def test_dispatch_prompt_is_exact_public_no_tools_and_excludes_answer_key() -> None:
    case = _case()
    dispatch = case.dispatch_prompt_text
    assert "NO-NETWORK, NO-TOOLS EVALUATION" in dispatch
    assert case.system_prompt in dispatch
    assert case.user_prompt in dispatch
    assert json.dumps(case.input_payload, sort_keys=True, separators=(",", ":")) in dispatch
    assert "sealed_answer_key" not in dispatch
    assert "human_rationale" not in dispatch
    assert sha256_hex(dispatch.encode("utf-8")) == case.prompt_sha256


def test_raw_model_output_is_frozen_with_computed_exact_hashes() -> None:
    case = _case()
    raw = {
        "case_id": case.case_id,
        "phase": case.phase.value,
        "model_identity": "GPT-5.6 Sol",
        "reasoning_setting": "xhigh",
        "conversation_id": "fresh-projectless-task",
        "output_text": '{"decision":"NO_CHANGE"}',
    }
    frozen = freeze_sol_output(case, raw)
    assert frozen.prompt_sha256 == case.prompt_sha256
    assert frozen.input_sha256 == case.input_sha256
    assert frozen.output_sha256 == sha256_hex(raw["output_text"].encode("utf-8"))
    validate_frozen_sol_output(case, frozen)


def test_three_conditions_share_one_frozen_output_and_noop_is_length_matched() -> None:
    case = _case()
    frozen = _frozen(case)
    conditions = compile_conditions(case, frozen)
    assert {item.condition for item in conditions} == set(ConditionKind)
    assert len({item.frozen_sol_output_sha256 for item in conditions}) == 1
    by_kind = {item.condition: item for item in conditions}
    assert by_kind[ConditionKind.PLAIN_SOL].output_text == frozen.output_text
    assert abs(
        len(by_kind[ConditionKind.NO_OP_LENGTH_MATCHED].output_text.encode("utf-8"))
        - len(by_kind[ConditionKind.SOLFORGE].output_text.encode("utf-8"))
    ) <= by_kind[ConditionKind.NO_OP_LENGTH_MATCHED].length_tolerance_bytes
    assert '"schema_version":"solforge_benchmark_compiled_v1"' not in (
        by_kind[ConditionKind.NO_OP_LENGTH_MATCHED].output_text
    )
    assert "source_hypothesis_text" not in by_kind[ConditionKind.SOLFORGE].output_text
    assert "source_output_sha256" not in by_kind[ConditionKind.SOLFORGE].output_text
    assert "compiler_version" not in by_kind[ConditionKind.SOLFORGE].output_text
    assert len(by_kind[ConditionKind.NO_OP_LENGTH_MATCHED].output_text) == len(
        by_kind[ConditionKind.SOLFORGE].output_text
    )


def test_governor_preserves_nonfatal_limitations_and_canonicalizes_factorial() -> None:
    case = replace(
        _case(),
        case_id="MUSK-FACTORIAL",
        category="two factor musk design",
        user_prompt="Design a complete two-factor comparison.",
        input_payload={
            "target_identity": "diffusive rounded musk",
            "ideal_architecture": {"Habanolide": "diffusion", "Romandolide": "volume"},
            "current_inventory_build": {"materials": []},
            "criterion": "DEPTH",
            "permitted_materials": ["Habanolide", "Romandolide"],
        },
        public_invariants=("zero_one_intervention", "complete_nary_arms", "authority_false"),
        sealed_answer_key={
            "allowed_decisions": ["PROPOSED"],
            "max_interventions": 1,
            "required_arm_sets": [[
                "CONTROL", "HABANOLIDE", "ROMANDOLIDE", "HABANOLIDE_X_ROMANDOLIDE"
            ]],
            "require_authority_false": True,
        },
    )
    raw = json.dumps(
        {
            "decision": "PROPOSED",
            "interventions": [{"type": "complete_factorial"}],
            "materials": ["Habanolide", "Romandolide"],
            "blockers": ["No physical observations are supplied."],
            "arms": [{"id": value} for value in ("A00", "A10", "A01", "A11")],
            "nary_factors": ["Habanolide", "Romandolide"],
            "next_comparison": "Run the four constant-total arms.",
            "authority_flags": BENCHMARK_AUTHORITY_FLAGS,
        },
        sort_keys=True,
    )
    frozen = FrozenSolOutputV1(
        case_id=case.case_id,
        phase=case.phase,
        model_identity="GPT-5.6 Sol",
        reasoning_setting="xhigh",
        conversation_id="factorial-task",
        prompt_sha256=case.prompt_sha256,
        input_sha256=case.input_sha256,
        output_text=raw,
        output_sha256=sha256_hex(raw.encode("utf-8")),
    )
    governed = next(
        item for item in compile_conditions(case, frozen)
        if item.condition is ConditionKind.SOLFORGE
    )
    payload = json.loads(governed.output_text)
    assert payload["decision"] == "PROPOSED"
    assert len(payload["interventions"]) == 1
    assert payload["arms"] == [
        "CONTROL", "HABANOLIDE", "ROMANDOLIDE", "HABANOLIDE_X_ROMANDOLIDE"
    ]
    assert payload["nary_factors"] == ["Habanolide", "Romandolide"]


def test_forced_hold_preserves_evidence_only_design_and_dependent_ratio_arms() -> None:
    case = replace(
        _case(),
        case_id="COUNT-HOLD",
        input_payload={
            **_case().input_payload,
            "criterion": "DEPTH",
            "permitted_materials": ["Iralia", "Orris Givco"],
            "required_hold_reasons": ["INGREDIENT_COUNT_RATIONALE"],
        },
    )
    output = json.dumps(
        {
            "decision": "HOLD",
            "interventions": [{"type": "CONSTANT_TOTAL_NARY_RATIO_SCREEN"}],
            "materials": ["Iralia", "Orris Givco"],
            "blockers": ["INGREDIENT_COUNT_RATIONALE"],
            "arms": ["IRALIA", "MIX", "ORRIS"],
            "nary_factors": [
                {"factor": "Iralia_fraction", "levels": [1.0, 0.5, 0.0]},
                {"factor": "Orris_Givco_fraction", "constraint": "1-Iralia_fraction"},
            ],
            "next_comparison": "Compare the three constant-total ratio arms.",
            "authority_flags": BENCHMARK_AUTHORITY_FLAGS,
        },
        sort_keys=True,
    )
    frozen = FrozenSolOutputV1(
        case_id=case.case_id,
        phase=case.phase,
        model_identity="GPT-5.6 Sol",
        reasoning_setting="xhigh",
        conversation_id="count-hold-task",
        prompt_sha256=case.prompt_sha256,
        input_sha256=case.input_sha256,
        output_text=output,
        output_sha256=sha256_hex(output.encode("utf-8")),
    )
    governed = next(
        item
        for item in compile_conditions(case, frozen)
        if item.condition is ConditionKind.SOLFORGE
    )
    payload = json.loads(governed.output_text)
    assert payload["decision"] == "HOLD"
    assert payload["interventions"] == [
        {
            "status": "EVIDENCE_ONLY_NOT_AUTHORIZED",
            "type": "CONSTANT_TOTAL_NARY_RATIO_SCREEN",
        }
    ]
    assert payload["arms"] == ["IRALIA", "MIX", "ORRIS"]
    assert "INCOMPLETE_NARY_ARMS" not in payload["blockers"]


def test_condition_set_rejects_condition_specific_resampling() -> None:
    case = _case()
    conditions = list(compile_conditions(case, _frozen(case)))
    conditions[1] = replace(conditions[1], frozen_sol_output_sha256="f" * 64)
    with pytest.raises(ValueError, match="one frozen Sol output"):
        score_invariants(case, tuple(conditions))


def test_blinded_packets_hide_labels_and_bind_unchanged_outputs() -> None:
    case = _case()
    conditions = compile_conditions(case, _frozen(case))
    packets, answer_key = blind_condition_outputs(
        case, conditions, seed=719
    )
    serialized = canonical_json_bytes([packet.as_dict() for packet in packets])
    for label in ConditionKind:
        assert label.value.encode("utf-8") not in serialized
    assert set(answer_key) == {packet.candidate_id for packet in packets}
    assert all("dispatch_prompt_text" not in packet.public_case for packet in packets)
    assert all("system_prompt" not in packet.public_case for packet in packets)
    assert all("sealed_answer_key" not in packet.public_case for packet in packets)
    with pytest.raises(ValueError, match="changed after blinding"):
        replace(packets[0], output_text=packets[0].output_text + " changed")


def test_judge_ingest_requires_unblinding_and_complete_unique_results() -> None:
    case = _case()
    packets, key = blind_condition_outputs(case, compile_conditions(case, _frozen(case)), seed=3)
    results = tuple(
        JudgeResultV1(
            packet_sha256=packet.record_sha256,
            candidate_id=packet.candidate_id,
            judge_model_identity="GPT-5.6 Sol",
            judge_reasoning_setting="xhigh",
            scores=(("clarity", 4), ("evidence_efficiency", 4)),
            critical_error=False,
            rationale="Bounded and evidence-aware.",
        )
        for packet in packets
    )
    with pytest.raises(PermissionError, match="unblinding"):
        ingest_judge_results(packets, results, key, unblinding_authorized=False)
    with pytest.raises(ValueError, match="missing judge result"):
        ingest_judge_results(packets, results[:-1], key, unblinding_authorized=True)
    with pytest.raises(ValueError, match="duplicate judge result"):
        ingest_judge_results(
            packets, (*results, results[0]), key, unblinding_authorized=True
        )
    mapped = ingest_judge_results(packets, results, key, unblinding_authorized=True)
    assert {item.condition for item in mapped} == set(ConditionKind)


def test_raw_judge_output_is_bound_to_exact_packets() -> None:
    case = _case()
    packets, _ = blind_condition_outputs(case, compile_conditions(case, _frozen(case)), seed=31)
    raw = {
        "case_id": case.case_id,
        "model_identity": "GPT-5.6 Sol",
        "reasoning_setting": "xhigh",
        "conversation_id": "fresh-judge-task",
        "prompt_text": "Judge these three anonymous candidates.",
        "output_text": json.dumps(
            {
                "results": [
                    {
                        "candidate_id": packet.candidate_id,
                        "scores": {"clarity": 4, "evidence_efficiency": 5},
                        "critical_error": False,
                        "rationale": "Bounded output.",
                    }
                    for packet in packets
                ]
            },
            sort_keys=True,
        ),
    }
    results = freeze_judge_output(packets, raw)
    assert len(results) == 3
    assert {result.packet_sha256 for result in results} == {
        packet.record_sha256 for packet in packets
    }
    changed = dict(raw)
    changed["output_text"] = json.dumps({"results": []})
    with pytest.raises(ValueError, match="missing judge result"):
        freeze_judge_output(packets, changed)


def test_judged_results_are_scored_on_declared_five_criterion_scale() -> None:
    case = _case()
    packets, key = blind_condition_outputs(
        case, compile_conditions(case, _frozen(case)), seed=43
    )
    results = tuple(
        JudgeResultV1(
            packet_sha256=packet.record_sha256,
            candidate_id=packet.candidate_id,
            judge_model_identity="GPT-5.6 Sol",
            judge_reasoning_setting="xhigh",
            scores=(
                ("target_fidelity", 5),
                ("experimental_usefulness", 4),
                ("restraint", 3),
                ("clarity", 2),
                ("evidence_efficiency", 1),
            ),
            critical_error=packet is packets[0],
            rationale="Bounded score.",
        )
        for packet in packets
    )
    mapped = ingest_judge_results(
        packets, results, key, unblinding_authorized=True
    )
    scored = score_judged_results(mapped)
    assert len(scored) == 3
    assert all(row["score"] == 15 for row in scored)
    assert all(row["score_max"] == 25 for row in scored)
    assert sum(bool(row["critical_errors"]) for row in scored) == 1

    incomplete = replace(results[0], scores=(("clarity", 5),))
    remapped = ingest_judge_results(
        packets,
        (incomplete, *results[1:]),
        key,
        unblinding_authorized=True,
    )
    with pytest.raises(ValueError, match="five declared criteria"):
        score_judged_results(remapped)


def test_invariant_scoring_is_deterministic_and_authority_closed() -> None:
    case = _case()
    conditions = compile_conditions(case, _frozen(case))
    first = score_invariants(case, conditions)
    second = score_invariants(case, conditions)
    assert [item.canonical_bytes() for item in first] == [
        item.canonical_bytes() for item in second
    ]
    compiled = next(item for item in first if item.condition is ConditionKind.SOLFORGE)
    assert compiled.critical_errors == ()
    assert compiled.failed_invariants == ()
    assert compiled.score == 100
    assert compiled.authority_flags == tuple(sorted(BENCHMARK_AUTHORITY_FLAGS.items()))


def test_complete_frozen_outputs_reject_missing_duplicate_and_phase_leakage() -> None:
    screen = _case()
    confirmation = replace(
        _case(phase=BenchmarkPhase.CONFIRMATION), case_id="CONFIRM-001"
    )
    frozen = _frozen(screen)
    with pytest.raises(ValueError, match="missing case"):
        assert_complete_frozen_outputs((screen, confirmation), (frozen,))
    with pytest.raises(ValueError, match="duplicate case"):
        assert_complete_frozen_outputs((screen,), (frozen, frozen))
    leaked = replace(frozen, case_id=confirmation.case_id)
    with pytest.raises(ValueError, match="phase"):
        assert_complete_frozen_outputs((confirmation,), (leaked,))


def test_admission_requires_declared_thresholds_and_zero_critical_errors() -> None:
    admitted = BenchmarkAdmissionV1.evaluate(
        module_id="ARCHITECTURAL_DELTA",
        phase=BenchmarkPhase.CONFIRMATION,
        wins_vs_plain=4,
        wins_vs_noop=5,
        total_cases=6,
        median_gain_vs_plain=6.0,
        median_gain_vs_noop=5.0,
        critical_errors=(),
    )
    assert admitted.admitted is True
    rejected = BenchmarkAdmissionV1.evaluate(
        module_id="ARCHITECTURAL_DELTA",
        phase=BenchmarkPhase.CONFIRMATION,
        wins_vs_plain=6,
        wins_vs_noop=6,
        total_cases=6,
        median_gain_vs_plain=20.0,
        median_gain_vs_noop=20.0,
        critical_errors=("AUTHORITY_ESCALATION",),
    )
    assert rejected.admitted is False
    assert rejected.authority_flags == tuple(sorted(BENCHMARK_AUTHORITY_FLAGS.items()))
