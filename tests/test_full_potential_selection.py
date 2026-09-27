"""Checkpoint 17 conservative search and withholding behavior."""

from __future__ import annotations

import pytest

from engine.research.selection import (
    OfflineCandidateV1,
    compare_search_arms,
    lavender_ambrox_search_contract,
)


def _candidate(index: int, *, interval_width: float = 0.01) -> OfflineCandidateV1:
    x = index / 80.0
    loss = (x - 0.35) ** 2
    return OfflineCandidateV1(
        candidate_id=f"candidate-{index:03d}",
        variables={"lavender_active_mass_g": x, "ambrox_active_mass_g": 1.0 - x},
        endpoint_value=loss,
        prediction_interval=(loss - interval_width, loss + interval_width),
        coverage_decimal="1",
        applicability_state="APPLICABLE",
        feature_lineage=("delivered_gas_intensity_trajectory",),
        model_signs={"strongest": -1, "partial_addition": -1},
    )


def test_three_arms_receive_equal_unique_nonbaseline_budgets() -> None:
    result = compare_search_arms(
        tuple(_candidate(index) for index in range(81)),
        baseline_id="candidate-000",
        endpoint_id="measured_intensity_trajectory_loss",
        budget_per_arm=12,
        seeds=(17, 29),
    )
    assert result["benchmark_equal_budget"] is True
    assert set(result["algorithm_versions"]) == {
        "random", "simple_local", "conservative_gp"
    }
    for run in result["runs"]:
        for arm in run["arms"].values():
            assert arm["unique_feasible_nonbaseline_evaluations"] == 12
            assert len(arm["queried_candidate_ids"]) == 12


def test_insufficient_unique_pool_holds_instead_of_reusing_candidates() -> None:
    result = compare_search_arms(
        tuple(_candidate(index) for index in range(5)),
        baseline_id="candidate-000",
        endpoint_id="one-endpoint",
        budget_per_arm=5,
        seeds=(17,),
    )
    assert result["selection_status"] == "WITHHELD_INSUFFICIENT_UNIQUE_FEASIBLE_CANDIDATES"
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


@pytest.mark.parametrize(
    "feature",
    ["raw oav", "log-oav", "hand assigned valence", "ingredient count", "release score"],
)
def test_prohibited_beauty_proxies_are_rejected_at_schema_boundary(feature: str) -> None:
    with pytest.raises(ValueError, match="prohibited"):
        OfflineCandidateV1(
            candidate_id="bad",
            variables={"x": 1.0},
            endpoint_value=1.0,
            prediction_interval=(0.0, 2.0),
            coverage_decimal="1",
            applicability_state="APPLICABLE",
            feature_lineage=(feature,),
            model_signs={},
        )


def test_overlap_or_model_disagreement_forces_unordered_no_change() -> None:
    candidates = []
    for index in range(16):
        row = _candidate(index, interval_width=100.0)
        if index == 3:
            row = OfflineCandidateV1(
                **{
                    **row.as_dict(),
                    "model_signs": {"a": -1, "b": 1},
                }
            )
        candidates.append(row)
    result = compare_search_arms(
        candidates,
        baseline_id="candidate-000",
        endpoint_id="character-loss",
        budget_per_arm=5,
        seeds=(17,),
    )
    assert result["selection_status"] == "WITHHELD_NONDISCRIMINATING_EVIDENCE"
    assert result["ranked_candidates"] == []
    assert result["shortlist_ordering"] == "UNORDERED_DIVERSE_SET"
    assert result["formula_action"] == "NO_CHANGE"


def test_lavender_ambrox_contract_holds_until_common_active_mass_exists() -> None:
    held = lavender_ambrox_search_contract(
        accounting_result={"common_active_mass_basis_available": False},
        lavender_component_ids=("bontoux", "aroma-more"),
        ambrox_component_id="ambrox-crystals",
    )
    assert held["selection_status"] == "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED"
    assert held["variables"] == []
    assert held["crystal_ambrox_unit"] == "mg"

    admitted = lavender_ambrox_search_contract(
        accounting_result={
            "common_active_mass_basis_available": True,
            "total_active_mass_g_decimal": "5.9",
        },
        lavender_component_ids=("bontoux", "aroma-more"),
        ambrox_component_id="ambrox-crystals",
    )
    assert admitted["variables"][0]["fixed_internal_split"] == [70, 30]
    assert admitted["variables"][1]["physical_command_unit"] == "mg"
    assert admitted["frozen_non_target_rows"] is True
