from __future__ import annotations

from engine.perception.complexity_benchmark import (
    BenchmarkState,
    decide_paired_benchmark,
    score_structured_response,
)
from tests.complexity_benchmark_fixtures import (
    benchmark_evidence,
    case_by_id,
    telemetry_summary,
    valid_response,
)


def test_inventory_invention_is_critical_and_automatic_loss() -> None:
    case = case_by_id("CX-C01")
    response = valid_response(case)
    response["claims"].append(
        {
            "claim": "Ambrettolide was physically added",
            "state": "TESTED",
            "evidence_refs": [],
            "authority_ceiling": "PHYSICAL",
        }
    )
    score = score_structured_response(case, response)
    assert any(
        violation.code == "INVENTED_PHYSICAL_ADDITION" and violation.critical
        for violation in score.violations
    )
    assert score.total == 0


def test_mere_complication_cannot_score_as_richness() -> None:
    case = case_by_id("CX-A02")
    response = valid_response(case)
    response["depth_and_richness_analysis"]["coherent_richness"] = {
        "claim": "This is richer because it has more ingredients and descriptors.",
        "evidence_refs": [],
    }
    score = score_structured_response(case, response)
    assert any(
        violation.code == "COMPLICATION_AS_COMPLEXITY" and violation.critical
        for violation in score.violations
    )
    assert score.total == 0


def test_hedonic_potential_must_remain_an_untested_hypothesis() -> None:
    case = case_by_id("CX-D04")
    response = valid_response(case)
    response["depth_and_richness_analysis"]["hedonic_potential_hypotheses"][0][
        "state"
    ] = "TESTED"
    score = score_structured_response(case, response)
    assert any(
        violation.code == "UNSUPPORTED_HEDONIC_RESULT" and violation.critical
        for violation in score.violations
    )


def test_exception_only_musk_cannot_leak_into_build_or_count_as_depth() -> None:
    case = case_by_id("CX-C03")
    response = valid_response(case)
    response["current_inventory_build"]["materials"].append("Tonalide")
    response["depth_and_richness_analysis"]["coherent_richness"] = {
        "claim": "A three-musk chord is inherently richer.",
        "evidence_refs": [],
    }
    score = score_structured_response(case, response)
    codes = {item.code for item in score.violations if item.critical}
    assert {"MUSK_EXCEPTION_REQUIRED", "MUSK_COUNT_PROXY"}.issubset(codes)
    assert score.total == 0


def test_valid_response_scores_six_frozen_dimensions() -> None:
    case = case_by_id("CX-B02")
    score = score_structured_response(case, valid_response(case))
    assert score.dimension_scores.keys() == {
        "target_architecture",
        "integrated_depth_richness",
        "factual_provenance",
        "missing_chemical_impact",
        "controlled_test_quality",
        "uncertainty_conflict_actionability",
    }
    assert sum(score.dimension_scores.values()) == score.total
    assert score.total == 100
    assert not score.violations


def test_response_contract_rejects_extra_keys_and_missing_claim_states() -> None:
    case = case_by_id("CX-A01")
    response = valid_response(case)
    response["decorative_score"] = 99
    score = score_structured_response(case, response)
    assert score.total == 0
    assert {item.code for item in score.violations} == {
        "INVALID_STRUCTURED_RESPONSE"
    }


def test_ensemble_requires_all_five_thresholds() -> None:
    decision = decide_paired_benchmark(
        benchmark_evidence(
            wins=12,
            median_delta=5,
            new_critical=0,
            category_regression=0,
        ),
        telemetry=telemetry_summary(),
    )
    assert decision.state is BenchmarkState.OUTPERFORMS
    assert (
        decide_paired_benchmark(
            benchmark_evidence(wins=11, median_delta=5),
            telemetry=telemetry_summary(),
        ).state
        is BenchmarkState.INCONCLUSIVE
    )
    assert (
        decide_paired_benchmark(
            benchmark_evidence(wins=12, median_delta=4),
            telemetry=telemetry_summary(),
        ).state
        is BenchmarkState.INCONCLUSIVE
    )
    assert (
        decide_paired_benchmark(
            benchmark_evidence(wins=12, median_delta=5, new_critical=1),
            telemetry=telemetry_summary(),
        ).state
        is BenchmarkState.NO_DEMONSTRATED_OUTPERFORMANCE
    )


def test_cost_review_uses_exposed_comparable_price_only() -> None:
    decision = decide_paired_benchmark(
        benchmark_evidence(wins=12, median_delta=5),
        telemetry=telemetry_summary(treatment_price="2.01"),
    )
    assert decision.state is BenchmarkState.QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED
    not_exposed = telemetry_summary(state="NOT_EXPOSED")
    assert (
        decide_paired_benchmark(
            benchmark_evidence(wins=12, median_delta=5), telemetry=not_exposed
        ).state
        is BenchmarkState.OUTPERFORMS
    )
