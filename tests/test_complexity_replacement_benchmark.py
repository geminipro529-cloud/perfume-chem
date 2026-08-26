from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from engine.perception.complexity_module_retest import (
    ModulePairScore,
    ModuleRetestArm,
    ModuleRetestRole,
)
from engine.perception.complexity_replacement_benchmark import (
    REPLACEMENT_MODULE_IDS,
    ReplacementBenchmarkCase,
    ReplacementModulePacket,
    ReplacementScoredOutput,
    ReplacementScreenDecision,
    build_replacement_benchmark_manifest,
    build_replacement_benchmark_receipt,
    decide_replacement_retention,
    decide_replacement_screen,
    load_replacement_benchmark_cases,
    prepare_replacement_benchmark_request,
)

FIXTURES = Path(__file__).parent / "fixtures"
RUBRIC = (
    Path(__file__).parents[1]
    / "configs"
    / "complexity"
    / "complexity_replacement_benchmark_rubric_v1.json"
)


def _packet(module_id: str = "architectural_delta") -> ReplacementModulePacket:
    return ReplacementModulePacket(
        module_id=module_id,
        operating_contract=(
            "Choose zero or one target-ranked nonredundant delta.",
            "Ingredient count never proves complexity.",
        ),
        authority_boundary=(
            "No formula mutation authority.",
            "No physical or sensory authority.",
        ),
        evidence_refs=("engine:architectural-delta",),
    )


def _case(
    module_id: str = "architectural_delta",
    role: ModuleRetestRole = ModuleRetestRole.POSITIVE,
) -> ReplacementBenchmarkCase:
    return ReplacementBenchmarkCase(
        case_id="RPL-ARC-01",
        module_id=module_id,
        phase="SCREEN",
        role=role,
        target_identity="Precise iris depth with deliberate negative space",
        facts=("The current formula is target-faithful.", "No function is missing."),
        inventory_state={"state": "CURRENT_V5_BOUND"},
        expected_decision="NO_CHANGE",
        critical_error="INGREDIENT_COUNT_AS_COMPLEXITY",
        claim_ceiling="COMPUTATIONAL_DESIGN_ONLY",
        module_packet=_packet(module_id),
    )


def test_frozen_replacement_rubric_is_complete_and_hash_bound() -> None:
    rubric = json.loads(RUBRIC.read_text(encoding="utf-8"))
    expected_hash = RUBRIC.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]

    assert sum(item["points"] for item in rubric["criteria"]) == 100
    assert rubric["blinding"]["answer_keys_sent_to_generation_model"] is False
    assert not any(rubric["authority"].values())
    assert hashlib.sha256(RUBRIC.read_bytes()).hexdigest() == expected_hash


def test_replacement_modules_and_three_arm_prompts_are_frozen_and_fair() -> None:
    assert REPLACEMENT_MODULE_IDS == (
        "architectural_delta",
        "temporal_sensory_ledger",
        "hedonic_preference_learner",
    )
    case = _case()
    control = prepare_replacement_benchmark_request(case, ModuleRetestArm.CONTROL)
    treatment = prepare_replacement_benchmark_request(case, ModuleRetestArm.TREATMENT)
    placebo = prepare_replacement_benchmark_request(case, ModuleRetestArm.PLACEBO)

    assert "context_packet" not in control.prompt_payload
    treatment_packet = treatment.prompt_payload["context_packet"]
    placebo_packet = placebo.prompt_payload["context_packet"]
    assert treatment_packet != placebo_packet
    assert treatment_packet.keys() == placebo_packet.keys()
    assert treatment_packet["schema_version"] == placebo_packet["schema_version"]
    assert treatment.packet_byte_count == placebo.packet_byte_count
    assert "architectural_delta" not in str(treatment_packet)
    assert "engine/perception" not in str(treatment_packet)
    assert "placebo" not in str(placebo_packet).casefold()
    assert "treatment" not in str(treatment_packet).casefold()
    assert control.common_input_sha256 == treatment.common_input_sha256
    assert control.common_input_sha256 == placebo.common_input_sha256
    assert len({control.nonce, treatment.nonce, placebo.nonce}) == 3
    assert treatment.context_requirement == "FRESH_PROJECTLESS_CONVERSATION"
    assert control.prompt_payload["schema_version"].endswith("_v2_blinded")


def test_all_prompt_arms_hide_scorer_only_answer_keys() -> None:
    case = _case()

    for arm in ModuleRetestArm:
        request = prepare_replacement_benchmark_request(case, arm)
        prompt_case = request.prompt_payload["case"]

        assert "expected_decision" not in prompt_case
        assert "critical_error" not in prompt_case
        assert "case_id" not in prompt_case
        assert "module_id" not in prompt_case
        assert "phase" not in prompt_case
        assert "role" not in prompt_case
        assert case.expected_decision not in str(request.prompt_payload)
        assert case.critical_error not in str(request.prompt_payload)
        assert case.case_id not in str(request.prompt_payload)
        assert case.role.value not in str(request.prompt_payload)
        assert case.module_id not in str(request.prompt_payload)
        assert case.phase not in str(request.prompt_payload)
        assert "length_matched_placebo" not in str(request.prompt_payload)


def test_frozen_corpus_prompts_are_blind_across_every_case_and_arm() -> None:
    cases = load_replacement_benchmark_cases(
        FIXTURES / "complexity_replacement_retest_cases_v1.json"
    )

    for case in cases:
        for arm in ModuleRetestArm:
            request = prepare_replacement_benchmark_request(case, arm)
            prompt = str(request.prompt_payload)

            assert case.expected_decision not in prompt
            assert case.critical_error not in prompt
            assert case.case_id not in prompt
            assert case.module_id not in prompt
            assert case.phase not in prompt
            assert case.role.value not in prompt
            assert "module_packet" not in request.prompt_payload
            assert "length_matched_placebo" not in prompt


def test_v2_temporal_positive_case_requires_observed_endpoint_cells(
    tmp_path: Path,
) -> None:
    corpus_path = FIXTURES / "complexity_replacement_retest_cases_v2.json"
    expected_sha256 = (
        FIXTURES / "complexity_replacement_retest_cases_v2.sha256"
    ).read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(corpus_path.read_bytes()).hexdigest() == expected_sha256

    cases = load_replacement_benchmark_cases(corpus_path)
    temporal = next(case for case in cases if case.case_id == "RPL-TEM-S01")
    evidence = temporal.common_payload()["evidence_payload"]

    assert evidence["protocol_id"] == "TEMP-RPL-S01"
    assert evidence["sample_id"] == "BLIND-A"
    assert evidence["endpoint_id"] == "DEPTH_INTENSITY"
    assert len(evidence["observations"]) == 12
    assert {row["timepoint_seconds"] for row in evidence["observations"]} == {
        60,
        1800,
    }

    malformed = json.loads(corpus_path.read_text(encoding="utf-8"))
    row = next(item for item in malformed["cases"] if item["case_id"] == "RPL-TEM-S01")
    row.pop("evidence_payload")
    malformed_path = tmp_path / "malformed-v2.json"
    malformed_path.write_text(json.dumps(malformed), encoding="utf-8")

    with pytest.raises(ValueError, match="observed endpoint cells"):
        load_replacement_benchmark_cases(malformed_path)


def test_fresh_run_nonce_changes_request_identity_without_changing_prompt() -> None:
    case = _case()

    first = prepare_replacement_benchmark_request(
        case,
        ModuleRetestArm.TREATMENT,
        run_nonce="formal-run-20260824-a",
    )
    second = prepare_replacement_benchmark_request(
        case,
        ModuleRetestArm.TREATMENT,
        run_nonce="formal-run-20260824-b",
    )

    assert first.prompt_sha256 == second.prompt_sha256
    assert first.prompt_payload == second.prompt_payload
    assert first.common_input_sha256 == second.common_input_sha256
    assert first.nonce != second.nonce
    assert first.request_id != second.request_id


def _scores(
    *,
    roles: tuple[ModuleRetestRole, ...],
    control_scores: tuple[str, ...],
    treatment_scores: tuple[str, ...] | None = None,
    critical_regression: bool = False,
) -> tuple[ModulePairScore, ...]:
    treatment = treatment_scores or tuple("90" for _ in roles)
    return tuple(
        ModulePairScore(
            module_id="architectural_delta",
            case_id=f"RPL-ARC-{index:02d}",
            role=role,
            treatment_score=Decimal(treatment[index - 1]),
            control_score=Decimal(control_scores[index - 1]),
            critical_regression=critical_regression and index == 1,
            safe_countercase_pass=True,
            critical_trap_pass=True,
            specialist_checks_pass=True,
        )
        for index, role in enumerate(roles, start=1)
    )


def test_screen_requires_two_of_three_wins_against_each_control() -> None:
    roles = (
        ModuleRetestRole.POSITIVE,
        ModuleRetestRole.SAFE_COUNTERCASE,
        ModuleRetestRole.CRITICAL_TRAP,
    )
    plain = _scores(roles=roles, control_scores=("80", "85", "91"))
    placebo = _scores(roles=roles, control_scores=("82", "91", "88"))

    passed = decide_replacement_screen(plain, placebo)
    assert passed.state == "PROCEED"
    assert passed.plain_control_wins == 2
    assert passed.placebo_wins == 2

    failed = decide_replacement_screen(
        plain,
        _scores(roles=roles, control_scores=("82", "91", "88"), critical_regression=True),
    )
    assert failed.state == "STOP"
    assert "CRITICAL_REGRESSION" in failed.reasons


def test_screen_differences_under_one_point_are_ties() -> None:
    roles = (
        ModuleRetestRole.POSITIVE,
        ModuleRetestRole.SAFE_COUNTERCASE,
        ModuleRetestRole.CRITICAL_TRAP,
    )
    submargin_controls = _scores(
        roles=roles,
        control_scores=("89.5", "89.5", "89.5"),
    )

    decision = decide_replacement_screen(submargin_controls, submargin_controls)

    assert decision.state == "STOP"
    assert decision.plain_control_wins == 0
    assert decision.placebo_wins == 0
    assert "PLAIN_CONTROL_TWO_WINS_REQUIRED" in decision.reasons
    assert "PLACEBO_TWO_WINS_REQUIRED" in decision.reasons


def test_scored_output_rejects_nonzero_score_with_critical_error() -> None:
    with pytest.raises(
        ValueError,
        match="critical errors require a zero rubric score",
    ):
        ReplacementScoredOutput(
            request_id="rplreq-critical",
            output_text="Unsafe unsupported authority claim.",
            rubric_score=Decimal("75"),
            evaluator_id="replacement-blind-rubric-v1",
            critical_error_codes=("UNSUPPORTED_AUTHORITY",),
            safe_countercase_pass=False,
            critical_trap_pass=False,
            specialist_checks_pass=False,
        )


def test_final_differences_under_one_point_are_ties() -> None:
    roles = tuple(ModuleRetestRole)
    submargin_controls = _scores(
        roles=roles,
        control_scores=tuple("89.5" for _ in roles),
    )

    decision = decide_replacement_retention(
        submargin_controls,
        submargin_controls,
    )

    assert decision.plain_control_decision.treatment_wins == 0
    assert decision.placebo_decision.treatment_wins == 0


def test_final_admission_requires_four_wins_and_five_points_against_both() -> None:
    roles = tuple(ModuleRetestRole)
    plain = _scores(roles=roles, control_scores=("80", "82", "84", "80", "85", "83"))
    placebo = _scores(roles=roles, control_scores=("82", "83", "85", "81", "84", "82"))

    admitted = decide_replacement_retention(plain, placebo)
    assert admitted.state == "ADMITTED"
    assert admitted.plain_control_decision.median_paired_delta >= Decimal("5")
    assert admitted.placebo_decision.median_paired_delta >= Decimal("5")

    weak_placebo = _scores(
        roles=roles,
        control_scores=("89", "89", "89", "89", "89", "89"),
    )
    rejected = decide_replacement_retention(plain, weak_placebo)
    assert rejected.state == "RETAINED_AS_PROVENANCE_TOMBSTONE"
    assert any(reason.startswith("PLACEBO:") for reason in rejected.reasons)


def test_fresh_corpus_has_three_screen_and_three_confirmation_cases_per_module() -> None:
    corpus_path = FIXTURES / "complexity_replacement_retest_cases_v2.json"
    corpus_sha256 = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    expected_sha256 = (
        FIXTURES / "complexity_replacement_retest_cases_v2.sha256"
    ).read_text(encoding="utf-8").split()[0]
    assert corpus_sha256 == expected_sha256
    cases = load_replacement_benchmark_cases(corpus_path)
    assert len(cases) == 18
    for module_id in REPLACEMENT_MODULE_IDS:
        selected = tuple(case for case in cases if case.module_id == module_id)
        assert len(selected) == 6
        assert [case.phase for case in selected].count("SCREEN") == 3
        assert [case.phase for case in selected].count("CONFIRM") == 3
        assert {case.role for case in selected} == set(ModuleRetestRole)

    manifest = build_replacement_benchmark_manifest(
        cases=cases,
        corpus_sha256=corpus_sha256,
        rubric_sha256="f" * 64,
        run_nonce="replacement-xhigh-test-run",
        phase="ALL",
        model_identity={
            "provider": "OpenAI",
            "product": "ChatGPT",
            "model": "test-xhigh-snapshot",
            "reasoning_effort": "Extra High",
            "surface": "Work",
            "context": "FRESH_PROJECTLESS_CONVERSATION",
        },
    )
    assert len(manifest["requests"]) == 54
    assert manifest["run_nonce"] == "replacement-xhigh-test-run"
    assert manifest["rubric_sha256"] == "f" * 64
    assert manifest["schema_version"].endswith("_v5_blinded")
    assert manifest["old_frozen_requests_resumed"] is False
    assert manifest["authority"] == {
        "formula": False,
        "inventory": False,
        "physical_execution": False,
        "sensory": False,
        "safety": False,
        "purchase": False,
        "publication": False,
        "release": False,
    }
    for request in manifest["requests"]:
        canonical_payload = json.dumps(
            request["prompt_payload"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        assert request["dispatch_text"].endswith(canonical_payload)
        assert hashlib.sha256(request["dispatch_text"].encode("utf-8")).hexdigest() == (
            request["dispatch_sha256"]
        )
        assert f'"arm":"{request["arm"]}"' not in request["dispatch_text"]

    outputs = tuple(
        ReplacementScoredOutput(
            request_id=request["request_id"],
            output_text=f"Frozen response for {request['request_id']}",
            rubric_score=Decimal("90"),
            evaluator_id="blind-rubric-v1",
            critical_error_codes=(),
            safe_countercase_pass=True,
            critical_trap_pass=True,
            specialist_checks_pass=True,
        )
        for request in manifest["requests"]
    )
    receipt = build_replacement_benchmark_receipt(
        run_id="replacement-xhigh-test-run",
        manifest=manifest,
        scored_outputs=outputs,
    )
    assert receipt["result_count"] == 54
    assert receipt["schema_version"].endswith("_v5_blinded")
    assert receipt["phase"] == "ALL"
    assert receipt["rollback_policy"] == manifest["rollback_policy"]
    assert receipt["rubric_sha256"] == manifest["rubric_sha256"]
    assert receipt["manifest_sha256"] == manifest["manifest_sha256"]
    assert receipt["results"][0]["output_sha256"]
    assert receipt["results"][0]["dispatch_sha256"] == manifest["requests"][0][
        "dispatch_sha256"
    ]
    assert receipt["results"][0]["rubric_score"] == "90"
    assert receipt["authority"] == manifest["authority"]


def test_live_manifest_is_screen_first_and_confirmation_is_receipt_gated() -> None:
    corpus_path = FIXTURES / "complexity_replacement_retest_cases_v2.json"
    cases = load_replacement_benchmark_cases(corpus_path)
    common = {
        "cases": cases,
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "rubric_sha256": "f" * 64,
        "run_nonce": "replacement-xhigh-screen-first",
        "model_identity": {
            "provider": "OpenAI",
            "product": "ChatGPT",
            "model": "test-xhigh-snapshot",
            "reasoning_effort": "Extra High",
            "surface": "Work",
            "context": "FRESH_PROJECTLESS_CONVERSATION",
        },
    }

    screen = build_replacement_benchmark_manifest(**common, phase="SCREEN")

    assert screen["phase"] == "SCREEN"
    assert screen["request_count"] == 27
    assert {request["phase"] for request in screen["requests"]} == {"SCREEN"}
    assert screen["rollback_policy"]["source_deletion_authorized"] is False
    assert screen["rollback_policy"]["runtime_reachable_during_benchmark"] is False
    assert screen["rollback_policy"]["post_restore_verification_required"] is True
    assert screen["rollback_policy"]["rollback_failure_state"] == (
        "HOLD_RUNTIME_UNREACHABLE"
    )

    screen_outputs = tuple(
        ReplacementScoredOutput(
            request_id=request["request_id"],
            output_text=f"Frozen screen response for {request['request_id']}",
            rubric_score=(
                Decimal("0")
                if request["arm"] == "TREATMENT"
                and request["module_id"] != "temporal_sensory_ledger"
                else Decimal("90")
                if request["arm"] == "TREATMENT"
                else Decimal("80")
                if request["module_id"] == "temporal_sensory_ledger"
                and request["role"] != "CRITICAL_TRAP"
                else Decimal("90")
            ),
            evaluator_id="blind-rubric-v1",
            critical_error_codes=(
                ("SYNTHETIC_CRITICAL_REGRESSION",)
                if request["arm"] == "TREATMENT"
                and request["module_id"] != "temporal_sensory_ledger"
                else ()
            ),
            safe_countercase_pass=True,
            critical_trap_pass=True,
            specialist_checks_pass=True,
        )
        for request in screen["requests"]
    )
    screen_receipt = build_replacement_benchmark_receipt(
        run_id="replacement-xhigh-screen-first",
        manifest=screen,
        scored_outputs=screen_outputs,
    )

    decisions = tuple(
        ReplacementScreenDecision(
            module_id=module_id,
            state="PROCEED" if module_id == "temporal_sensory_ledger" else "STOP",
            plain_control_wins=(
                2 if module_id == "temporal_sensory_ledger" else 0
            ),
            placebo_wins=(2 if module_id == "temporal_sensory_ledger" else 0),
            reasons=(
                ()
                if module_id == "temporal_sensory_ledger"
                else (
                    "PLAIN_CONTROL_TWO_WINS_REQUIRED",
                    "PLACEBO_TWO_WINS_REQUIRED",
                    "CRITICAL_REGRESSION",
                )
            ),
        )
        for module_id in REPLACEMENT_MODULE_IDS
    )
    confirmation = build_replacement_benchmark_manifest(
        **common,
        phase="CONFIRM",
        screen_decisions=decisions,
        screen_receipt=screen_receipt,
    )

    assert confirmation["phase"] == "CONFIRM"
    assert confirmation["request_count"] == 9
    assert {request["module_id"] for request in confirmation["requests"]} == {
        "temporal_sensory_ledger"
    }
    assert {request["phase"] for request in confirmation["requests"]} == {"CONFIRM"}
    assert confirmation["screen_receipt_sha256"] == screen_receipt["receipt_sha256"]

    fabricated_decisions = tuple(
        ReplacementScreenDecision(
            module_id=decision.module_id,
            state="PROCEED",
            plain_control_wins=2,
            placebo_wins=2,
            reasons=(),
        )
        if decision.module_id == "architectural_delta"
        else decision
        for decision in decisions
    )
    with pytest.raises(ValueError, match="screen decisions do not match"):
        build_replacement_benchmark_manifest(
            **common,
            phase="CONFIRM",
            screen_decisions=fabricated_decisions,
            screen_receipt=screen_receipt,
        )

    with pytest.raises(ValueError, match="screen receipt"):
        build_replacement_benchmark_manifest(
            **common,
            phase="CONFIRM",
            screen_decisions=decisions,
        )

    tampered = dict(screen_receipt)
    tampered["result_count"] = 26
    with pytest.raises(ValueError, match="screen receipt hash"):
        build_replacement_benchmark_manifest(
            **common,
            phase="CONFIRM",
            screen_decisions=decisions,
            screen_receipt=tampered,
        )


def test_screen_decision_cannot_claim_proceed_with_insufficient_wins() -> None:
    with pytest.raises(ValueError, match="PROCEED"):
        ReplacementScreenDecision(
            module_id="architectural_delta",
            state="PROCEED",
            plain_control_wins=1,
            placebo_wins=3,
            reasons=(),
        )


def test_v3_corpus_refreshes_sensory_safety_and_reliability_without_mutating_v2() -> None:
    v2_path = FIXTURES / "complexity_replacement_retest_cases_v2.json"
    v2_hash = hashlib.sha256(v2_path.read_bytes()).hexdigest()
    assert v2_hash == (
        FIXTURES / "complexity_replacement_retest_cases_v2.sha256"
    ).read_text(encoding="utf-8").split()[0]

    v3_path = FIXTURES / "complexity_replacement_retest_cases_v3.json"
    v3_hash = hashlib.sha256(v3_path.read_bytes()).hexdigest()
    assert v3_hash == (
        FIXTURES / "complexity_replacement_retest_cases_v3.sha256"
    ).read_text(encoding="utf-8").split()[0]
    cases = load_replacement_benchmark_cases(v3_path)

    positive = next(case for case in cases if case.case_id == "RPL-TEM-S01")
    safety = next(case for case in cases if case.case_id == "RPL-TEM-C03")
    assert positive.evidence_payload["repeatability"] == {
        "required": True,
        "maximum_within_assessor_repeat_spread": 1.0,
    }
    assert safety.expected_decision.startswith("HOLD")
    assert safety.critical_error == "ADVERSE_SENSORY_EVENT_IGNORED"
    assert safety.evidence_payload["safety_events"][0]["event_code"] == "HEADACHE"
    assert any(
        "safety incident" in rule.casefold()
        for rule in safety.module_packet.operating_contract
    )
    assert any(
        "repeatability" in rule.casefold()
        for rule in safety.module_packet.operating_contract
    )
