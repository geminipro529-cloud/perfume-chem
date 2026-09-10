from __future__ import annotations

from engine.perception.cypress_benchmark import (
    BenchmarkCondition,
    BenchmarkStage,
    ScoredBenchmarkResponse,
    build_cypress_xhigh_admission_pack,
    evaluate_cypress_admission,
)


def test_pack_contains_three_screen_and_three_confirmation_cases() -> None:
    pack = build_cypress_xhigh_admission_pack()

    assert len(pack.cases) == 6
    assert sum(case.stage is BenchmarkStage.SCREEN for case in pack.cases) == 3
    assert sum(case.stage is BenchmarkStage.CONFIRMATION for case in pack.cases) == 3
    assert len({case.case_id for case in pack.cases}) == 6
    assert not any("frozen-27" in case.case_id for case in pack.cases)


def test_integrated_and_placebo_prompts_are_exactly_length_matched() -> None:
    pack = build_cypress_xhigh_admission_pack()

    for case in pack.cases:
        integrated = pack.render_prompt(case.case_id, BenchmarkCondition.INTEGRATED)
        placebo = pack.render_prompt(case.case_id, BenchmarkCondition.PLACEBO)
        assert len(integrated.encode("utf-8")) == len(placebo.encode("utf-8"))
        assert integrated != placebo
        assert pack.prompt_sha256(case.case_id, BenchmarkCondition.INTEGRATED) != (
            pack.prompt_sha256(case.case_id, BenchmarkCondition.PLACEBO)
        )


def test_all_conditions_share_case_payload_output_contract_and_model_identity() -> None:
    pack = build_cypress_xhigh_admission_pack()

    assert pack.model == "gpt-5.6-sol"
    assert pack.reasoning_effort == "xhigh"
    for case in pack.cases:
        prompts = {
            condition: pack.render_prompt(case.case_id, condition)
            for condition in BenchmarkCondition
        }
        for prompt in prompts.values():
            assert case.case_payload in prompt
            assert pack.output_contract in prompt
            assert "Return exactly one JSON object" in prompt


def test_hidden_scoring_is_non_scalar_across_distinct_criteria() -> None:
    pack = build_cypress_xhigh_admission_pack()

    assert sum(weight for _, weight in pack.scoring_dimensions) == 100
    assert tuple(name for name, _ in pack.scoring_dimensions) == (
        "TARGET_FIDELITY",
        "RELATIONAL_DEPTH",
        "INVENTORY_TRUTH",
        "EVIDENCE_AND_AUTHORITY",
        "EXPERIMENTAL_DISCRIMINATION",
        "USABILITY_AND_DETAIL",
    )
    assert pack.critical_errors
    assert "ingredient count" in " ".join(pack.critical_errors).casefold()


def test_case_pack_covers_required_traps_and_safe_countercases() -> None:
    pack = build_cypress_xhigh_admission_pack()
    tags = {tag for case in pack.cases for tag in case.tags}

    assert {
        "INGREDIENT_COUNT_TRAP",
        "INVENTORY_MISMATCH",
        "INHERITED_IRIS_MODEL_TRAP",
        "PRECISE_SIMPLICITY_COUNTERCASE",
        "ORDER_CONFOUNDING",
        "UNSEEN_TARGET_VARIANT",
    } <= tags


def test_pack_freezes_every_prompt_hash_for_reproducibility() -> None:
    first = build_cypress_xhigh_admission_pack()
    second = build_cypress_xhigh_admission_pack()

    assert first.record_sha256 == second.record_sha256
    assert first.prompt_manifest() == second.prompt_manifest()
    assert len(first.prompt_manifest()) == 18


def test_screening_gate_requires_two_wins_against_each_control() -> None:
    pack = build_cypress_xhigh_admission_pack()
    screen_ids = [
        case.case_id for case in pack.cases if case.stage is BenchmarkStage.SCREEN
    ]
    scores: list[ScoredBenchmarkResponse] = []
    plain = (80.0, 95.0, 80.0)
    placebo = (95.0, 80.0, 80.0)
    for index, case_id in enumerate(screen_ids):
        scores.extend(
            (
                ScoredBenchmarkResponse(
                    case_id, BenchmarkCondition.INTEGRATED, 90.0
                ),
                ScoredBenchmarkResponse(
                    case_id, BenchmarkCondition.PLAIN, plain[index]
                ),
                ScoredBenchmarkResponse(
                    case_id, BenchmarkCondition.PLACEBO, placebo[index]
                ),
            )
        )

    result = evaluate_cypress_admission(pack, scores, BenchmarkStage.SCREEN)

    assert result.passed is True
    assert result.case_count == 3
    assert result.wins_vs_plain == 2
    assert result.wins_vs_placebo == 2


def test_any_integrated_critical_error_blocks_screening() -> None:
    pack = build_cypress_xhigh_admission_pack()
    scores: list[ScoredBenchmarkResponse] = []
    for case in pack.cases:
        if case.stage is not BenchmarkStage.SCREEN:
            continue
        critical_errors = (
            ("claims observed liking",)
            if case.case_id == "CYP-XH-S1-COUNT-TRAP"
            else ()
        )
        scores.extend(
            (
                ScoredBenchmarkResponse(
                    case.case_id,
                    BenchmarkCondition.INTEGRATED,
                    100.0,
                    critical_errors,
                ),
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.PLAIN, 70.0
                ),
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.PLACEBO, 70.0
                ),
            )
        )

    result = evaluate_cypress_admission(pack, scores, BenchmarkStage.SCREEN)

    assert result.passed is False
    assert result.integrated_critical_errors == ("claims observed liking",)


def test_full_gate_requires_four_wins_and_five_point_median_gain_per_control() -> None:
    pack = build_cypress_xhigh_admission_pack()
    scores: list[ScoredBenchmarkResponse] = []
    plain = (80.0, 80.0, 80.0, 80.0, 95.0, 95.0)
    placebo = (84.0, 84.0, 84.0, 84.0, 84.0, 84.0)
    for index, case in enumerate(pack.cases):
        scores.extend(
            (
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.INTEGRATED, 90.0
                ),
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.PLAIN, plain[index]
                ),
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.PLACEBO, placebo[index]
                ),
            )
        )

    result = evaluate_cypress_admission(pack, scores, None)

    assert result.passed is True
    assert result.case_count == 6
    assert result.wins_vs_plain == 4
    assert result.wins_vs_placebo == 6
    assert result.median_gain_vs_plain == 10.0
    assert result.median_gain_vs_placebo == 6.0


def test_full_gate_rejects_sub_five_point_median_gain() -> None:
    pack = build_cypress_xhigh_admission_pack()
    scores: list[ScoredBenchmarkResponse] = []
    for case in pack.cases:
        scores.extend(
            (
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.INTEGRATED, 90.0
                ),
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.PLAIN, 86.0
                ),
                ScoredBenchmarkResponse(
                    case.case_id, BenchmarkCondition.PLACEBO, 84.0
                ),
            )
        )

    result = evaluate_cypress_admission(pack, scores, None)

    assert result.passed is False
    assert result.wins_vs_plain == 6
    assert result.median_gain_vs_plain == 4.0
