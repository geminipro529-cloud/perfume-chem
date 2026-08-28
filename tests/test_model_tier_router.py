from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engine.solforge.model_tier_router import (
    MODEL_TIER_AUTHORITY_FLAGS,
    ModelTaskClass,
    ModelTier,
    ModelTierRequest,
    ModelTierRouteState,
    TierBenchmarkReceipt,
    load_model_tier_policy,
    route_model_tier,
)

CONTRACT_SHA = "a" * 64
INPUT_SHA = "b" * 64
CORPUS_SHA = "c" * 64
PROMPT_SHA = "d" * 64
BENCHMARK_INPUT_SHA = "e" * 64
CANDIDATE_OUTPUT_SHA = "f" * 64
REFERENCE_OUTPUT_SHA = "1" * 64
SCORE_SHA = "2" * 64


def _request(
    task_class: ModelTaskClass,
    *,
    requested_tier: ModelTier | None = None,
    benchmark_receipts: tuple[TierBenchmarkReceipt, ...] = (),
    contract_frozen: bool = True,
    machine_checkable: bool = True,
    **overrides: object,
) -> ModelTierRequest:
    values: dict[str, object] = {
        "request_id": "MODEL-ROUTE-001",
        "task_class": task_class,
        "frozen_contract_sha256": CONTRACT_SHA,
        "input_sha256": INPUT_SHA,
        "requested_tier": requested_tier,
        "contract_frozen": contract_frozen,
        "machine_checkable": machine_checkable,
        "open_source_conflict": False,
        "open_critical_regression": False,
        "changes_authority": False,
        "benchmark_receipts": benchmark_receipts,
    }
    values.update(overrides)
    return ModelTierRequest(**values)


def _xhigh_receipt(**overrides: object) -> TierBenchmarkReceipt:
    values: dict[str, object] = {
        "receipt_id": "XHIGH-VS-ULTRA-001",
        "task_class": ModelTaskClass.FROZEN_RULE_APPLICATION,
        "candidate_tier": ModelTier.SOL_XHIGH,
        "reference_tier": ModelTier.SOL_ULTRA,
        "frozen_contract_sha256": CONTRACT_SHA,
        "benchmark_corpus_sha256": CORPUS_SHA,
        "prompt_bundle_sha256": PROMPT_SHA,
        "input_bundle_sha256": BENCHMARK_INPUT_SHA,
        "candidate_model_identity": "GPT-5.6 Sol xhigh",
        "reference_model_identity": "GPT-5.6 Sol Ultra",
        "screen_case_count": 3,
        "screen_win_count": 2,
        "confirmation_case_count": 6,
        "confirmation_win_count": 4,
        "confirmation_nonloss_count": 5,
        "exact_confirmation_agreement_count": 5,
        "median_paired_delta": 0.0,
        "unseen_variants_present": True,
        "mutation_cases_present": True,
        "adversarial_cases_present": True,
        "deterministic_replay": True,
        "critical_error_count": 0,
        "hold_regression_count": 0,
        "authority_regression_count": 0,
        "candidate_output_bundle_sha256": CANDIDATE_OUTPUT_SHA,
        "reference_output_bundle_sha256": REFERENCE_OUTPUT_SHA,
        "score_bundle_sha256": SCORE_SHA,
    }
    values.update(overrides)
    return TierBenchmarkReceipt(**values)


def _normal_receipt(**overrides: object) -> TierBenchmarkReceipt:
    values: dict[str, object] = {
        "receipt_id": "NORMAL-VS-XHIGH-001",
        "task_class": ModelTaskClass.FROZEN_RULE_APPLICATION,
        "candidate_tier": ModelTier.SOL_NORMAL_FAST,
        "reference_tier": ModelTier.SOL_XHIGH,
        "frozen_contract_sha256": CONTRACT_SHA,
        "benchmark_corpus_sha256": "3" * 64,
        "prompt_bundle_sha256": "4" * 64,
        "input_bundle_sha256": "5" * 64,
        "candidate_model_identity": "GPT-5.6 Sol Fast",
        "reference_model_identity": "GPT-5.6 Sol xhigh",
        "screen_case_count": 6,
        "screen_win_count": 6,
        "confirmation_case_count": 12,
        "confirmation_win_count": 12,
        "confirmation_nonloss_count": 12,
        "exact_confirmation_agreement_count": 12,
        "median_paired_delta": 0.0,
        "unseen_variants_present": True,
        "mutation_cases_present": True,
        "adversarial_cases_present": True,
        "deterministic_replay": True,
        "critical_error_count": 0,
        "hold_regression_count": 0,
        "authority_regression_count": 0,
        "candidate_output_bundle_sha256": "6" * 64,
        "reference_output_bundle_sha256": "7" * 64,
        "score_bundle_sha256": "8" * 64,
    }
    values.update(overrides)
    return TierBenchmarkReceipt(**values)


@pytest.mark.parametrize(
    "task_class",
    (
        ModelTaskClass.ARCHITECTURE_DESIGN,
        ModelTaskClass.HEDONIC_INTERPRETATION,
        ModelTaskClass.SCIENTIFIC_TRANSFER,
        ModelTaskClass.SOURCE_CONFLICT_RESOLUTION,
        ModelTaskClass.CROSS_MODULE_SYNTHESIS,
        ModelTaskClass.GATE_CHANGE,
        ModelTaskClass.MODULE_ADMISSION_RETIREMENT,
    ),
)
def test_open_judgment_and_governance_work_stays_ultra(
    task_class: ModelTaskClass,
) -> None:
    result = route_model_tier(
        _request(task_class, contract_frozen=False, machine_checkable=False)
    )

    assert result.state is ModelTierRouteState.APPROVED
    assert result.selected_tier is ModelTier.SOL_ULTRA
    assert result.authority_flags == MODEL_TIER_AUTHORITY_FLAGS


@pytest.mark.parametrize(
    "task_class",
    (
        ModelTaskClass.DETERMINISTIC_PARSE,
        ModelTaskClass.DETERMINISTIC_HASH,
        ModelTaskClass.DETERMINISTIC_SCHEMA_VALIDATION,
        ModelTaskClass.DETERMINISTIC_TEST_EXECUTION,
        ModelTaskClass.DETERMINISTIC_INVENTORY_JOIN,
    ),
)
def test_frozen_machine_checkable_work_uses_no_model(
    task_class: ModelTaskClass,
) -> None:
    result = route_model_tier(_request(task_class))

    assert result.state is ModelTierRouteState.APPROVED
    assert result.selected_tier is ModelTier.NO_MODEL_DETERMINISTIC


def test_deterministic_label_does_not_bypass_an_unfrozen_or_uncheckable_contract() -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.DETERMINISTIC_PARSE,
            contract_frozen=False,
            machine_checkable=False,
        )
    )

    assert result.selected_tier is ModelTier.SOL_ULTRA
    assert "DETERMINISTIC_PRECONDITIONS_NOT_MET" in result.reasons


def test_frozen_rule_application_remains_ultra_without_a_passing_xhigh_receipt() -> None:
    result = route_model_tier(_request(ModelTaskClass.FROZEN_RULE_APPLICATION))

    assert result.selected_tier is ModelTier.SOL_ULTRA
    assert "XHIGH_NONINFERIORITY_NOT_PROVEN" in result.reasons


def test_passing_exact_scope_xhigh_receipt_permits_xhigh() -> None:
    receipt = _xhigh_receipt()
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            benchmark_receipts=(receipt,),
        )
    )

    assert result.state is ModelTierRouteState.APPROVED
    assert result.selected_tier is ModelTier.SOL_XHIGH
    assert result.xhigh_benchmark_receipt_sha256 == receipt.record_sha256


@pytest.mark.parametrize(
    "failed_receipt",
    (
        _xhigh_receipt(screen_win_count=1),
        _xhigh_receipt(screen_case_count=30, screen_win_count=2),
        _xhigh_receipt(confirmation_win_count=3),
        _xhigh_receipt(
            confirmation_case_count=60,
            confirmation_win_count=4,
            confirmation_nonloss_count=5,
        ),
        _xhigh_receipt(confirmation_nonloss_count=4),
        _xhigh_receipt(median_paired_delta=-0.01),
        _xhigh_receipt(unseen_variants_present=False),
        _xhigh_receipt(adversarial_cases_present=False),
        _xhigh_receipt(critical_error_count=1),
        _xhigh_receipt(hold_regression_count=1),
        _xhigh_receipt(authority_regression_count=1),
        _xhigh_receipt(frozen_contract_sha256="9" * 64),
    ),
)
def test_failed_or_wrong_scope_xhigh_receipt_cannot_retire_ultra(
    failed_receipt: TierBenchmarkReceipt,
) -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            benchmark_receipts=(failed_receipt,),
        )
    )

    assert result.selected_tier is ModelTier.SOL_ULTRA
    assert result.xhigh_benchmark_receipt_sha256 is None


def test_normal_fast_requires_both_xhigh_proof_and_exact_normal_agreement() -> None:
    xhigh = _xhigh_receipt()
    normal = _normal_receipt()
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            benchmark_receipts=(normal, xhigh),
        )
    )

    assert result.selected_tier is ModelTier.SOL_NORMAL_FAST
    assert result.xhigh_benchmark_receipt_sha256 == xhigh.record_sha256
    assert result.normal_benchmark_receipt_sha256 == normal.record_sha256


def test_normal_receipt_alone_cannot_skip_the_xhigh_stage() -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            benchmark_receipts=(_normal_receipt(),),
        )
    )

    assert result.selected_tier is ModelTier.SOL_ULTRA


@pytest.mark.parametrize(
    "failed_receipt",
    (
        _normal_receipt(screen_case_count=5, screen_win_count=5),
        _normal_receipt(confirmation_case_count=11, confirmation_win_count=11,
                        confirmation_nonloss_count=11,
                        exact_confirmation_agreement_count=11),
        _normal_receipt(exact_confirmation_agreement_count=11),
        _normal_receipt(mutation_cases_present=False),
        _normal_receipt(deterministic_replay=False),
        _normal_receipt(critical_error_count=1),
    ),
)
def test_failed_normal_receipt_stops_at_xhigh(
    failed_receipt: TierBenchmarkReceipt,
) -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            benchmark_receipts=(_xhigh_receipt(), failed_receipt),
        )
    )

    assert result.selected_tier is ModelTier.SOL_XHIGH
    assert result.normal_benchmark_receipt_sha256 is None


def test_request_for_unproven_lower_tier_returns_explicit_escalation() -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            requested_tier=ModelTier.SOL_NORMAL_FAST,
        )
    )

    assert result.state is ModelTierRouteState.ESCALATE
    assert result.selected_tier is ModelTier.SOL_ULTRA
    assert result.requested_tier is ModelTier.SOL_NORMAL_FAST


@pytest.mark.parametrize(
    ("override", "reason"),
    (
        ({"open_source_conflict": True}, "OPEN_SOURCE_CONFLICT"),
        ({"open_critical_regression": True}, "OPEN_CRITICAL_REGRESSION"),
        ({"changes_authority": True}, "AUTHORITY_CHANGE_REQUIRES_ULTRA"),
    ),
)
def test_runtime_risk_triggers_force_ultra(
    override: dict[str, bool],
    reason: str,
) -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.FROZEN_RULE_APPLICATION,
            benchmark_receipts=(_xhigh_receipt(), _normal_receipt()),
            **override,
        )
    )

    assert result.selected_tier is ModelTier.SOL_ULTRA
    assert reason in result.reasons


def test_no_model_can_grant_safety_or_release_authority() -> None:
    result = route_model_tier(
        _request(
            ModelTaskClass.SAFETY_RELEASE_AUTHORITY,
            requested_tier=ModelTier.SOL_ULTRA,
            contract_frozen=False,
            machine_checkable=False,
        )
    )

    assert result.state is ModelTierRouteState.HOLD_HUMAN_AUTHORITY
    assert result.selected_tier is None
    assert result.authority_flags == MODEL_TIER_AUTHORITY_FLAGS


def test_policy_loader_rejects_unknown_fields_and_hashes_exact_bytes(tmp_path) -> None:
    policy = load_model_tier_policy()
    copied = json.loads(policy.canonical_bytes())
    copied["unreviewed_speed_override"] = True
    path = tmp_path / "bad-policy.json"
    path.write_text(json.dumps(copied), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown policy fields"):
        load_model_tier_policy(path)

    policy_again = load_model_tier_policy()
    assert policy.record_sha256 == policy_again.record_sha256


def test_policy_loader_rejects_weakened_thresholds_or_route_reassignment(tmp_path) -> None:
    policy = load_model_tier_policy()
    weakened = json.loads(policy.canonical_bytes())
    weakened["xhigh_noninferiority"]["min_screen_cases"] = 1
    weakened["xhigh_noninferiority"]["min_screen_wins"] = 1
    weak_path = tmp_path / "weak-policy.json"
    weak_path.write_text(json.dumps(weakened), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot weaken"):
        load_model_tier_policy(weak_path)

    reassigned = json.loads(policy.canonical_bytes())
    reassigned["task_routes"]["ARCHITECTURE_DESIGN"] = "BENCHMARK_GATED"
    route_path = tmp_path / "reassigned-policy.json"
    route_path.write_text(json.dumps(reassigned), encoding="utf-8")
    with pytest.raises(ValueError, match="task route"):
        load_model_tier_policy(route_path)


def test_receipts_and_route_results_are_deterministic_and_strictly_typed() -> None:
    receipt = _xhigh_receipt()
    result_a = route_model_tier(
        _request(ModelTaskClass.FROZEN_RULE_APPLICATION, benchmark_receipts=(receipt,))
    )
    result_b = route_model_tier(
        _request(ModelTaskClass.FROZEN_RULE_APPLICATION, benchmark_receipts=(receipt,))
    )

    assert result_a.canonical_bytes() == result_b.canonical_bytes()
    assert result_a.record_sha256 == result_b.record_sha256
    assert result_a.request_sha256 == _request(
        ModelTaskClass.FROZEN_RULE_APPLICATION,
        benchmark_receipts=(receipt,),
    ).record_sha256
    assert result_a.authority_flags == MODEL_TIER_AUTHORITY_FLAGS
    with pytest.raises(TypeError, match="screen_case_count"):
        replace(receipt, screen_case_count=True)


def test_benchmark_receipt_strict_round_trip_rejects_unknown_or_coerced_fields() -> None:
    receipt = _xhigh_receipt()
    assert TierBenchmarkReceipt.from_dict(receipt.as_dict()) == receipt
    unknown = receipt.as_dict()
    unknown["convenient_override"] = True
    with pytest.raises(ValueError, match="unknown receipt fields"):
        TierBenchmarkReceipt.from_dict(unknown)
    coerced = receipt.as_dict()
    coerced["screen_case_count"] = "3"
    with pytest.raises(TypeError, match="screen_case_count"):
        TierBenchmarkReceipt.from_dict(coerced)
