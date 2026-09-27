"""Checkpoint 19 frozen comparator and completion-state contracts."""

from __future__ import annotations

from hashlib import sha256

from engine.research.comparison import (
    ComparatorEvidenceV1,
    compare_design_evidence,
    project_completion_states,
)


def _row(name: str, value: float, interval: tuple[float, float], **changes) -> ComparatorEvidenceV1:
    values = {
        "comparator_id": name,
        "formula_sha256": sha256(name.encode("utf-8")).hexdigest(),
        "inventory_sha256": "1" * 64,
        "scenario_sha256": "2" * 64,
        "capability_bundle_sha256": "3" * 64,
        "active_accounting": {"total_active_mass_g": "5"},
        "release_coverage_decimal": "1",
        "endpoint_results": {
            "character_loss": {
                "value": value,
                "uncertainty_interval": interval,
                "applicability_state": "APPLICABLE",
            }
        },
        "physically_tested": False,
    }
    values.update(changes)
    return ComparatorEvidenceV1(**values)


def test_frozen_comparators_can_support_endpoint_only_ordering() -> None:
    result = compare_design_evidence(
        (
            _row("R5", 3.0, (2.9, 3.1)),
            _row("R6", 2.0, (1.9, 2.1)),
            _row("NEW", 1.0, (0.9, 1.1)),
        ),
        ordered_endpoint="character_loss",
    )
    assert [row["comparator_id"] for row in result["ranked_comparators"]] == [
        "NEW", "R6", "R5"
    ]
    assert "SUPPORTED_ENDPOINT_IMPROVEMENT" in result["classifications"]
    assert "NOT_PHYSICALLY_TESTED" in result["classifications"]
    assert result["formula_action"] == "PROPOSE_ONLY"
    assert result["release_authority"] is False


def test_coverage_or_scenario_difference_forbids_complete_ranking() -> None:
    coverage = compare_design_evidence(
        (
            _row("R5", 2.0, (1.9, 2.1)),
            _row("R6", 1.0, (0.9, 1.1), release_coverage_decimal="0.8"),
        ),
        ordered_endpoint="character_loss",
    )
    assert coverage["ranked_comparators"] == []
    assert "MODEL_COVERAGE_DIFFERS" in coverage["reason_codes"]
    scenario = compare_design_evidence(
        (
            _row("R5", 2.0, (1.9, 2.1)),
            _row("R6", 1.0, (0.9, 1.1), scenario_sha256="9" * 64),
        ),
        ordered_endpoint="character_loss",
    )
    assert "OUT_OF_DOMAIN" in scenario["classifications"]
    assert scenario["formula_action"] == "NO_CHANGE"


def test_overlapping_uncertainty_finishes_as_unordered_no_change() -> None:
    result = compare_design_evidence(
        (_row("R5", 1.0, (0.0, 2.0)), _row("R6", 1.1, (0.1, 2.1))),
        ordered_endpoint="character_loss",
    )
    assert result["ranked_comparators"] == []
    assert result["unordered_comparators"] == ["R5", "R6"]
    assert "NONDISCRIMINATING_EVIDENCE" in result["classifications"]
    assert result["formula_action"] == "NO_CHANGE"


def test_completion_states_are_independent_and_commercial_is_external() -> None:
    state = project_completion_states(
        generic_platform_contracts_pass=True,
        computational_comparison_complete=False,
        personal_selection_complete=False,
        qualified_commercial_release_receipt_present=False,
    )
    assert state["PLATFORM_SOFTWARE_COMPLETE"] is True
    assert state["R6_COMPUTATIONAL_EVIDENCE_COMPLETE"] is False
    assert state["PERSONAL_SELECTION_COMPLETE"] is False
    assert state["COMMERCIAL_RELEASE_READY"] is False
    assert state["automatic_commercial_authority"] is False
