"""Current three-comparator report must withhold unsupported ordering."""

from __future__ import annotations

import json
from pathlib import Path

from engine.calibration.hashing import (
    PORTABLE_FILE_HASH_MATCH_ALGORITHM,
)
from engine.experiments.checkpoint19_comparison import (
    evaluate_checkpoint19_comparison_boundary,
)
from tests.historical_snapshots import assert_historical_artifact

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = (
    ROOT
    / "data"
    / "governance"
    / "full_potential_cp10_cp19_acceptance_20260927.json"
)


def test_current_comparator_boundary_is_deterministic_and_unranked() -> None:
    first = evaluate_checkpoint19_comparison_boundary()
    second = evaluate_checkpoint19_comparison_boundary()
    assert first == second
    assert len(first["comparators"]) == 3
    assert first["selection"] == {
        "status": "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
        "ranked_candidates": [],
        "pareto_candidates": [],
        "unordered_candidates": [
            "lavande-ambre-profond-r5-30ml-20260923",
            "lavande-ambre-profond-r6-aimi-design-successor-20260926",
            "LAP-PARALLEL-A-20260927",
        ],
        "best_observed_candidate": None,
        "experimental_recommendation": None,
        "formula_action": "NO_CHANGE",
    }
    assert set(first["classifications"]) == {
        "COMPUTATIONALLY_DIFFERENT",
        "NONDISCRIMINATING_EVIDENCE",
        "NOT_PHYSICALLY_TESTED",
        "OUT_OF_DOMAIN",
    }
    assert first["completion_states"] == {
        "PLATFORM_SOFTWARE_COMPLETE": True,
        "R6_COMPUTATIONAL_EVIDENCE_COMPLETE": False,
        "PERSONAL_SELECTION_COMPLETE": False,
        "COMMERCIAL_RELEASE_READY": False,
    }
    assert first["completion_boundary"] == {
        "platform_basis": (
            "GENERIC_IDENTITY_AUTHORITY_JOB_RELEASE_PERCEPTION_OPTIMIZER_"
            "OBSERVATION_AND_PHYSICAL_LINEAGE_CONTRACTS_IMPLEMENTED"
        ),
        "computational_evidence_state": "WITHHELD_OUT_OF_DOMAIN",
        "personal_selection_state": "NOT_TESTED",
        "commercial_state_source": "OUTSIDE_AUTOMATIC_PROJECT_BOUNDARY",
        "automatic_commercial_authority": False,
    }
    assert all(
        comparator["release_scenario_sha256"] is None
        and comparator["release_coverage_decimal"] == "0"
        and comparator["physically_tested"] is False
        for comparator in first["comparators"]
    )


def test_current_comparator_boundary_keeps_crystal_mass_separate() -> None:
    report = evaluate_checkpoint19_comparison_boundary()
    assert all(
        comparator["physical_totals"]["liquid_total_uL"] == "5600"
        and comparator["physical_totals"]["solid_total_mg"] == "300"
        for comparator in report["comparators"]
    )
    assert all(
        comparator["active_accounting"]["common_active_mass_basis_available"]
        is False
        for comparator in report["comparators"]
    )
    assert report["formula_action"] == "NO_CHANGE"


def test_historical_platform_completion_receipt_preserves_its_own_source_pins() -> None:
    receipt = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == "full-potential-cp10-cp19-acceptance-v2"
    assert receipt["artifact_hash_semantics"] == (
        PORTABLE_FILE_HASH_MATCH_ALGORITHM
    )
    states = receipt["completion_states"]
    assert states["PLATFORM_SOFTWARE_COMPLETE"] is True
    assert states["R6_COMPUTATIONAL_EVIDENCE_COMPLETE"] is False
    assert states["PERSONAL_SELECTION_COMPLETE"] is False
    assert states["COMMERCIAL_RELEASE_READY"] is False
    assert receipt["goal_directed_analysis"]["status"] == (
        "SOFTWARE_COMPLETE_RESEARCH_HYPOTHESES_ONLY"
    )
    assert receipt["goal_directed_analysis"]["live_lavender_goal_smoke"][
        "formula_modified"
    ] is False
    assert receipt["final_executable_source_performance_matrix"][
        "serial_parallel_scientific_authority_status_mismatches"
    ] == 0
    assert receipt["authority"] == {
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
        "evidence_admission_authorized": False,
    }

    for relative_path, expected_sha256 in receipt["artifact_sha256"].items():
        artifact = ROOT / relative_path
        assert artifact.is_file(), relative_path
        assert_historical_artifact(artifact, expected_sha256)
