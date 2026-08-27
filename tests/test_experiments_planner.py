"""Tests for engine.experiments.planner."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.experiments.planner import (
    ExperimentPlan,
    compute_utility,
    suggest_omission_test,
    suggest_addition_range,
    design_blind_trial,
    suggest_material_pair_test,
)
import pytest


# ── compute_utility ───────────────────────────────────────────────────────────


def test_compute_utility_nominal():
    """gain=1.0, sensory=1.0, cost=1, irrev=0.5, time=5 → ~0.4"""
    u = compute_utility(gain=1.0, sensory=1.0, cost_ul=1.0, irreversibility=0.5, time_min=5)
    # denominator = max(1,1) * max(0.5,0.1) * max(5,5) = 1 * 0.5 * 5 = 2.5
    # numerator = 1 * 1 = 1
    # result = 1 / 2.5 = 0.4
    assert u == pytest.approx(0.4, abs=1e-9)


def test_compute_utility_worst_case():
    """gain=0, sensory=0 → 0"""
    u = compute_utility(gain=0.0, sensory=0.0, cost_ul=100.0, irreversibility=0.9, time_min=120)
    assert u == 0.0


def test_compute_utility_best_case():
    """gain=1, sensory=1, cost=1, irrev=0.1, time=5 → ~2.0"""
    u = compute_utility(gain=1.0, sensory=1.0, cost_ul=1.0, irreversibility=0.1, time_min=5)
    # denominator = max(1,1) * max(0.1,0.1) * max(5,5) = 1 * 0.1 * 5 = 0.5
    # numerator = 1 * 1 = 1
    # result = 1 / 0.5 = 2.0
    assert u == pytest.approx(2.0, abs=1e-9)


def test_compute_utility_clamps_cost_to_one():
    """cost_ul=0 should be clamped to 1 to avoid division by zero."""
    u = compute_utility(gain=0.5, sensory=0.5, cost_ul=0.0, irreversibility=0.2, time_min=10)
    # denominator = max(0,1) * max(0.2,0.1) * max(10,5) = 1 * 0.2 * 10 = 2.0
    # numerator = 0.5 * 0.5 = 0.25
    # result = 0.25 / 2.0 = 0.125
    assert u == pytest.approx(0.125, abs=1e-9)


def test_compute_utility_clamps_irreversibility():
    """irreversibility=0 should be clamped to 0.1."""
    u = compute_utility(gain=1.0, sensory=1.0, cost_ul=10.0, irreversibility=0.0, time_min=10)
    # denominator = max(10,1) * max(0,0.1) * max(10,5) = 10 * 0.1 * 10 = 10
    # result = 1 / 10 = 0.1
    assert u == pytest.approx(0.1, abs=1e-9)


def test_compute_utility_clamps_time():
    """time_min=1 should be clamped to 5."""
    u = compute_utility(gain=1.0, sensory=1.0, cost_ul=1.0, irreversibility=0.5, time_min=1)
    # denominator = max(1,1) * max(0.5,0.1) * max(1,5) = 1 * 0.5 * 5 = 2.5
    # result = 1 / 2.5 = 0.4
    assert u == pytest.approx(0.4, abs=1e-9)


# ── suggest_omission_test ─────────────────────────────────────────────────────


def test_suggest_omission_test_returns_plan():
    materials = [
        {"name": "Bergamot", "role": "character", "dose_ul": 50},
        {"name": "Hedione", "role": "radiance", "dose_ul": 300},
        {"name": "Iso E Super", "role": "signature", "dose_ul": 200},
    ]
    plan = suggest_omission_test(materials)
    assert isinstance(plan, ExperimentPlan)
    # 2 character/signature materials + 1 reference = 3 variants
    assert plan.variant_count > 1
    assert plan.variant_count == 3


def test_suggest_omission_test_instructions_non_empty():
    materials = [
        {"name": "Bergamot", "role": "character", "dose_ul": 50},
    ]
    plan = suggest_omission_test(materials)
    assert len(plan.instructions) > 0
    # Instructions should mention the material name
    assert any("Bergamot" in instr for instr in plan.instructions)


def test_suggest_omission_test_estimated_cost_positive():
    materials = [
        {"name": "Bergamot", "role": "character", "dose_ul": 50},
        {"name": "Iso E Super", "role": "signature", "dose_ul": 200},
    ]
    plan = suggest_omission_test(materials)
    assert plan.estimated_cost_ul > 0
    assert plan.estimated_cost_ul == pytest.approx(250.0, abs=1e-6)


def test_suggest_omission_test_no_character_materials():
    materials = [
        {"name": "Bergamot", "role": "top", "dose_ul": 50},
        {"name": "Hedione", "role": "radiance", "dose_ul": 300},
    ]
    plan = suggest_omission_test(materials)
    assert plan.variant_count == 0
    assert plan.estimated_cost_ul == 0.0
    assert "no character/signature materials found" in plan.description


def test_suggest_omission_test_empty_list():
    plan = suggest_omission_test([])
    assert plan.variant_count == 0
    assert plan.estimated_cost_ul == 0.0


# ── suggest_addition_range ────────────────────────────────────────────────────


def test_suggest_addition_range_three_variants():
    plan = suggest_addition_range("Ambrox Super", center_dose_ul=200.0)
    assert isinstance(plan, ExperimentPlan)
    assert plan.variant_count == 3


def test_suggest_addition_range_utility_computed():
    plan = suggest_addition_range("Ambrox Super", center_dose_ul=200.0)
    assert plan.utility_score > 0


def test_suggest_addition_range_doses_in_instructions():
    plan = suggest_addition_range("Ambrox Super", center_dose_ul=200.0)
    instructions_text = "\n".join(plan.instructions)
    assert "100.0" in instructions_text  # 50% of 200
    assert "200.0" in instructions_text  # centre
    assert "300.0" in instructions_text  # 150% of 200


def test_suggest_addition_range_cost():
    plan = suggest_addition_range("Test Material", center_dose_ul=100.0)
    # low=50, centre=100, high=150 → total=300
    assert plan.estimated_cost_ul == pytest.approx(300.0, abs=1e-6)


# ── design_blind_trial ────────────────────────────────────────────────────────


def test_design_blind_trial_returns_codes():
    samples = [
        {"label": "Formula A", "formula": "Bergamot 50 + Hedione 300"},
        {"label": "Formula B", "formula": "Bergamot 80 + Hedione 250"},
    ]
    plan = design_blind_trial(samples)
    assert isinstance(plan, ExperimentPlan)
    assert plan.variant_count == 2
    # Instructions should contain 3-letter codes
    instructions_text = "\n".join(plan.instructions)
    # Each code is 3 uppercase letters
    import re

    codes_found = re.findall(r"\b[A-Z]{3}\b", instructions_text)
    assert len(codes_found) >= 2


def test_design_blind_trial_instructions_mention_time_points():
    samples = [
        {"label": "Test", "formula": "Some formula"},
    ]
    plan = design_blind_trial(samples)
    instructions_text = "\n".join(plan.instructions)
    assert "0 min" in instructions_text
    assert "5 min" in instructions_text
    assert "30 min" in instructions_text
    assert "120 min" in instructions_text


def test_design_blind_trial_empty_samples():
    plan = design_blind_trial([])
    assert plan.variant_count == 0
    assert "no samples provided" in plan.description


def test_design_blind_trial_no_material_cost():
    samples = [
        {"label": "A", "formula": "formula A"},
        {"label": "B", "formula": "formula B"},
    ]
    plan = design_blind_trial(samples)
    assert plan.estimated_cost_ul == 0.0


# ── suggest_material_pair_test ────────────────────────────────────────────────


def test_suggest_material_pair_test_four_variants():
    plan = suggest_material_pair_test("Hedione", "Iso E Super", dose_a=100.0, dose_b=200.0)
    assert isinstance(plan, ExperimentPlan)
    assert plan.variant_count == 4


def test_suggest_material_pair_test_variant_labels():
    plan = suggest_material_pair_test("Hedione", "Iso E Super", dose_a=100.0, dose_b=200.0)
    instructions_text = "\n".join(plan.instructions)
    assert "Neither" in instructions_text
    assert "Hedione only" in instructions_text
    assert "Iso E Super only" in instructions_text
    assert "Both" in instructions_text


def test_suggest_material_pair_test_cost():
    plan = suggest_material_pair_test("A", "B", dose_a=50.0, dose_b=150.0)
    assert plan.estimated_cost_ul == pytest.approx(200.0, abs=1e-6)


def test_suggest_material_pair_test_utility():
    plan = suggest_material_pair_test("A", "B", dose_a=50.0, dose_b=150.0)
    assert plan.utility_score > 0


# ── ExperimentPlan as_dict / from_dict round-trip ─────────────────────────────


def test_experiment_plan_as_dict():
    plan = ExperimentPlan(
        plan_id="test-123",
        description="Test plan",
        variant_count=3,
        estimated_cost_ul=150.0,
        estimated_time_minutes=45,
        irreversibility=0.2,
        expected_information_gain=0.7,
        expected_sensory_value=0.8,
        utility_score=0.35,
        instructions=("Step 1", "Step 2", "Step 3"),
    )
    d = plan.as_dict()
    assert d["plan_id"] == "test-123"
    assert d["variant_count"] == 3
    assert d["estimated_cost_ul"] == 150.0
    assert d["instructions"] == ("Step 1", "Step 2", "Step 3")


def test_experiment_plan_from_dict_round_trip():
    plan = ExperimentPlan(
        plan_id="roundtrip-456",
        description="Round trip test",
        variant_count=2,
        estimated_cost_ul=99.9,
        estimated_time_minutes=30,
        irreversibility=0.1,
        expected_information_gain=0.5,
        expected_sensory_value=0.6,
        utility_score=0.25,
        instructions=("Do X", "Do Y"),
    )
    d = plan.as_dict()
    restored = ExperimentPlan(**d)
    assert restored == plan
    assert restored.plan_id == plan.plan_id
    assert restored.instructions == plan.instructions
    assert restored.utility_score == plan.utility_score


def test_experiment_plan_defaults():
    plan = ExperimentPlan(plan_id="defaults-test", description="Defaults")
    assert plan.variant_count == 1
    assert plan.estimated_cost_ul == 0.0
    assert plan.estimated_time_minutes == 30
    assert plan.irreversibility == 0.0
    assert plan.expected_information_gain == 0.0
    assert plan.expected_sensory_value == 0.0
    assert plan.utility_score == 0.0
    assert plan.instructions == ()


def test_experiment_plan_frozen():
    plan = ExperimentPlan(plan_id="frozen", description="Frozen test")
    with pytest.raises(AttributeError):
        plan.description = "mutated"  # type: ignore[misc]
