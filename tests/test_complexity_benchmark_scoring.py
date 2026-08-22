from __future__ import annotations

from decimal import Decimal

import pytest

from engine.perception.complexity_benchmark import (
    AblationObservation,
    BenchmarkState,
    FailureSummary,
    FamilyDecision,
    classify_repair,
    decide_family_ablation,
    decide_paired_benchmark,
    propose_registry_transition,
    score_structured_response,
)
from engine.perception.complexity_registry import ModuleRole
from tests.complexity_benchmark_fixtures import (
    benchmark_evidence,
    case_by_id,
    module_descriptor,
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


def test_capability_retains_on_gain_or_win_rate() -> None:
    rows = tuple(
        AblationObservation(
            f"CX-A0{index + 1}", Decimal(value), value > 0, 0
        )
        for index, value in enumerate((4, 3, 0, 5))
    )
    assert (
        decide_family_ablation(
            "construction_profile", ModuleRole.CAPABILITY, rows
        ).state
        == "RETAIN"
    )


def test_guardrail_retains_only_by_preventing_critical_failure() -> None:
    retained_rows = (AblationObservation("CX-B01", Decimal("0"), False, 1),)
    retained = decide_family_ablation(
        "admission_lifecycle", ModuleRole.GUARDRAIL, retained_rows
    )
    assert retained.state == "RETAIN"
    no_prevention = (AblationObservation("CX-B01", Decimal("10"), True, 0),)
    not_retained = decide_family_ablation(
        "admission_lifecycle", ModuleRole.GUARDRAIL, no_prevention
    )
    assert not_retained.state == "REPAIR_REQUIRED"


def test_no_relevant_case_is_not_failure_and_repair_count_is_capped() -> None:
    assert (
        decide_family_ablation("x", ModuleRole.CAPABILITY, []).state
        == "NOT_EVALUATED_NO_RELEVANT_CASE"
    )
    with pytest.raises(ValueError, match="one repair cycle"):
        classify_repair(
            FailureSummary(codes=("AUTHORITY_LEAK",), case_ids=("CX-B01",)),
            prior_repair_count=1,
        )


def test_repair_class_is_bounded_to_named_files_and_four_sealed_holdouts() -> None:
    decision = classify_repair(
        FailureSummary(
            codes=("UNSUPPORTED_HEDONIC_RESULT",),
            case_ids=("CX-D04",),
        ),
        prior_repair_count=0,
    )
    assert decision.repair_class.value == "AUTHORITY_LEAK"
    assert len(decision.sealed_holdout_ids) == 4
    assert decision.automatic_source_edits is False
    assert set(decision.allowed_files) == {
        "engine/perception/complexity_ensemble.py",
        "engine/perception/complexity_adapters.py",
    }


def test_retirement_changes_registry_state_but_never_deletes_source() -> None:
    descriptor = module_descriptor()
    decision = FamilyDecision(
        family_id=descriptor.family_id,
        state="RETIRE",
        median_delta=Decimal("-2"),
        win_rate=Decimal("0.25"),
        prevented_critical_failures=0,
        reasons=("failed one repair and four holdouts",),
    )
    proposal = propose_registry_transition(descriptor, decision)
    assert proposal.new_state == "RETIRED_BENCHMARK_UNDERPERFORMER"
    assert proposal.delete_paths == ()
    assert proposal.preserve_paths == (descriptor.path,)


def test_new_critical_regression_forces_repair_even_with_score_gain() -> None:
    rows = (
        AblationObservation(
            "CX-A01",
            Decimal("9"),
            True,
            0,
            new_critical_regressions=1,
        ),
    )
    assert (
        decide_family_ablation(
            "construction_profile", ModuleRole.CAPABILITY, rows
        ).state
        == "REPAIR_REQUIRED"
    )
